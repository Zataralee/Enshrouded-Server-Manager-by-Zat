"""Account persistence and HTTP authorization for per-server mod management."""
import importlib.util
import json
from pathlib import Path
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("mod_permissions_test", ROOT / "enshrouded_manager/manager.py")
manager = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(manager)


class ModPermissionsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        paths = mock.patch.multiple(manager, DATA_DIR=self.root / "data",
                                    MANAGER_CONFIG=self.root / "data/config.json",
                                    MANAGER_LOG=self.root / "data/log")
        paths.start()
        self.addCleanup(paths.stop)
        self.owned = manager.default_instance("Owned", self.root / "owned")
        self.owned["owner_user_id"] = "owner"
        self.assigned = manager.default_instance("Assigned", self.root / "assigned")
        self.foreign = manager.default_instance("Foreign", self.root / "foreign")
        self.foreign["owner_user_id"] = "someone-else"
        cfg = manager.default_config()
        cfg["allow_local_bypass"] = False
        cfg["instances"] = [self.owned, self.assigned, self.foreign]
        cfg["selected_instance_id"] = self.foreign["id"]
        manager.save_json(manager.MANAGER_CONFIG, cfg)

    def test_new_accounts_and_role_promotions_default_to_mods(self):
        for role in ("admin", "server_owner", "user"):
            user = manager.create_manager_user({"username": "new-admin" if role == "admin" else role, "password": "test", "role": role})
            self.assertEqual(role != "user", "mods" in user["permissions"])
            self.assertEqual(role != "user", manager.has_permission(manager.find_user(user_id=user["id"]), "mods"))
        promoted = manager.update_manager_user("user", {"role": "server_owner", "permissions": ["logs"]})
        self.assertEqual(["logs", "mods"], promoted["permissions"])
        self.assertEqual([], promoted["assigned_instance_ids"])

    def test_existing_accounts_profiles_and_unused_owner_invites_migrate_once(self):
        cfg = manager.config()
        cfg.pop("mods_permission_migrated", None)
        cfg["users"] = [{"id": role, "role": role, "permissions": ["logs"],
                         "assigned_instance_ids": [self.assigned["id"]]}
                        for role in ("admin", "server_owner", "user")]
        cfg["invite_profiles"]["server_owner"]["permissions"] = ["setup"]
        cfg["invite_codes"] = [{"role": "server_owner", "permissions": ["control"]}]
        manager.save_json(manager.MANAGER_CONFIG, cfg)
        migrated = manager.config()
        for user in migrated["users"]:
            self.assertEqual(user["role"] != "user", "mods" in user["permissions"])
            self.assertEqual([self.assigned["id"]], user["assigned_instance_ids"])
        self.assertIn("mods", migrated["invite_profiles"]["server_owner"]["permissions"])
        self.assertIn("mods", migrated["invite_codes"][0]["permissions"])
        manager.update_manager_user("server_owner", {"role": "server_owner", "permissions": ["logs"]})
        self.assertNotIn("mods", manager.config()["users"][1]["permissions"])
        self.assertFalse(manager.migrate_config(manager.config()))

    def test_owner_invites_receive_default_mods_with_server_scope_preserved(self):
        cfg = manager.config()
        cfg["invite_codes"] = [{"id": "invite", "code": "OWNER-CODE", "role": "server_owner",
                                "permissions": ["setup"], "assigned_instance_ids": [self.owned["id"]],
                                "expires_at": "2999-01-01T00:00:00", "used_at": "", "invalidated_at": ""}]
        manager.save_json(manager.MANAGER_CONFIG, cfg)
        user = manager.redeem_invite_code({"code": "OWNER-CODE", "username": "invited", "password": "test",
                                           "steam_name": "test", "steam_email": "test@example.invalid"})
        self.assertIn("mods", user["permissions"])
        self.assertEqual([self.owned["id"]], user["assigned_instance_ids"])

    def start_http(self, user):
        self.user_id = user["id"] if user else None
        owner = self
        class Handler(manager.Handler):
            def current_user(self):
                return manager.find_user(user_id=owner.user_id) if owner.user_id else None
            def log_message(self, *args):
                pass
        self.http = manager.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.http.serve_forever, daemon=True).start()
        self.addCleanup(self.http.server_close)
        self.addCleanup(self.http.shutdown)
        self.eml = mock.Mock()
        for method in ("status", "enable", "change_mod", "config_file", "import_zip"):
            getattr(self.eml, method).return_value = {"ok": True}
        self.adapter = mock.patch.object(manager, "eml_for_instance", return_value=self.eml).start()
        self.addCleanup(mock.patch.stopall)
        sup = mock.Mock()
        sup.lock = threading.RLock()
        sup.status.return_value = {"running": False}
        mock.patch.object(manager, "supervisor", return_value=sup).start()
        return sup

    def request(self, route, method="GET", instance=None, origin=None):
        headers = {}
        payload = None
        if method == "GET" or route.endswith("upload"):
            route += "?instance_id=" + (instance or self.assigned["id"])
        if method == "POST":
            headers["Content-Type"] = "application/zip" if "/upload?" in route else "application/json"
            payload = b"test zip" if "/upload?" in route else json.dumps({
                "instance_id": instance or self.assigned["id"], "enabled": True,
                "mod_id": "test", "action": "enable", "file": "config.lua", "content": "test",
                "user_id": "admin", "permissions": ["mods"], "role": "admin"}).encode()
        if origin:
            headers["Origin"] = origin
        req = urllib.request.Request(f"http://127.0.0.1:{self.http.server_port}{route}", data=payload, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req) as response:
                return response.status
        except urllib.error.HTTPError as error:
            error.close()
            return error.code

    def test_ordinary_user_grant_revoke_and_all_mod_routes_enforce_scope(self):
        user = manager.create_manager_user({"username": "ordinary", "password": "test",
                                            "assigned_instance_ids": [self.assigned["id"]]})
        self.start_http(user)
        routes = [("/api/mods", "GET"), ("/api/mods/config", "GET"),
                  *[(f"/api/mods/{action}", "POST") for action in ("loader", "action", "config", "apply", "upload")]]
        for route, method in routes:
            self.assertEqual(403, self.request(route, method), (route, method))
        self.adapter.assert_not_called()
        manager.update_manager_user(user["id"], {"permissions": ["mods"]})
        self.assertEqual(["mods"], manager.find_user(user_id=user["id"])["permissions"])
        for route, method in routes:
            self.adapter.reset_mock()
            self.assertEqual(200, self.request(route, method), (route, method))
            self.adapter.assert_called_with(self.assigned["id"])
            self.adapter.reset_mock()
            for target in (self.foreign["id"], "missing"):
                self.assertEqual(403, self.request(route, method, target), (route, method, target))
            self.adapter.assert_not_called()
        manager.update_manager_user(user["id"], {"permissions": []})
        for route, method in routes:
            self.assertEqual(403, self.request(route, method), (route, method))

    def test_owner_has_only_owned_and_assigned_servers_and_no_global_eml_admin(self):
        user = manager.create_manager_user({"username": "owner", "password": "test", "role": "server_owner",
                                            "assigned_instance_ids": [self.assigned["id"]]})
        sup = self.start_http(user)
        for inst in (self.owned, self.assigned):
            self.assertEqual(200, self.request("/api/mods", instance=inst["id"]))
            self.assertEqual(200, self.request("/api/mods/loader", "POST", inst["id"]))
        self.assertEqual(403, self.request("/api/mods", instance=self.foreign["id"]))
        self.assertEqual(403, self.request("/api/eml/updates"))
        for action in ("check-update", "install-update", "rollback"):
            self.assertEqual(403, self.request(f"/api/eml/{action}", "POST"))
        self.assertEqual(403, self.request("/api/users/update", "POST"))
        self.assertEqual(403, self.request("/api/mods/loader", "POST", origin="https://other.invalid"))
        sup.status.return_value = {"running": True}
        self.assertEqual(500, self.request("/api/mods/loader", "POST"))

    def test_unassigned_and_unauthenticated_users_cannot_access_mods(self):
        user = manager.create_manager_user({"username": "unassigned", "password": "test", "permissions": ["mods"]})
        self.start_http(user)
        self.assertEqual(403, self.request("/api/mods"))
        self.user_id = None
        self.assertEqual(401, self.request("/api/mods"))
        self.assertEqual(401, self.request("/api/mods/upload", "POST"))
        self.adapter.assert_not_called()


if __name__ == "__main__":
    unittest.main()
