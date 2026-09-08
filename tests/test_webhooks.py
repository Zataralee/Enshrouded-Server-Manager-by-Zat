import importlib.util
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "enshrouded_manager" / "manager.py"
SPEC = importlib.util.spec_from_file_location("enshrouded_manager_test_module", MODULE_PATH)
manager = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(manager)


class WebhookTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.original_paths = (manager.DATA_DIR, manager.MANAGER_CONFIG, manager.MANAGER_LOG)
        manager.DATA_DIR = self.temp_path
        manager.MANAGER_CONFIG = self.temp_path / "manager_config.json"
        manager.MANAGER_LOG = self.temp_path / "manager.log"

        cfg = manager.default_config()
        cfg["instances"] = [
            manager.default_instance("Server One", self.temp_path / "server-one"),
            manager.default_instance("Server Two", self.temp_path / "server-two"),
        ]
        cfg["selected_instance_id"] = cfg["instances"][0]["id"]
        manager.save_json(manager.MANAGER_CONFIG, cfg)

    def tearDown(self):
        manager.DATA_DIR, manager.MANAGER_CONFIG, manager.MANAGER_LOG = self.original_paths
        self.temp_dir.cleanup()

    def add_webhook(self, instance_id, name, url):
        return manager.save_instance_webhook(instance_id, {
            "name": name,
            "enabled": True,
            "mode": "discord",
            "url": url,
            "events": ["server.started"],
        })

    def test_legacy_webhook_migrates_to_server_webhook_list(self):
        cfg = manager.default_config()
        instance = manager.default_instance("Legacy", self.temp_path / "legacy")
        instance.pop("webhooks")
        instance["webhook"] = {
            "enabled": True,
            "mode": "discord",
            "url": "https://example.com/legacy",
            "events": ["server.started"],
        }
        cfg["instances"] = [instance]

        self.assertTrue(manager.migrate_config(cfg))
        self.assertNotIn("webhook", instance)
        self.assertEqual(len(instance["webhooks"]), 1)
        self.assertEqual(instance["webhooks"][0]["name"], "Primary Webhook")
        self.assertEqual(instance["webhooks"][0]["url"], "https://example.com/legacy")

    def test_multiple_webhooks_are_scoped_to_the_requested_server(self):
        first, second = manager.instances()
        first_a = self.add_webhook(first["id"], "First A", "https://example.com/first-a")
        first_b = self.add_webhook(first["id"], "First B", "https://example.com/first-b")
        self.add_webhook(second["id"], "Second", "https://example.com/second")

        targets = manager.webhook_targets("server.started", instance_id=first["id"])

        self.assertEqual({item[1]["id"] for item in targets}, {first_a["id"], first_b["id"]})
        self.assertTrue(all(item[0]["id"] == first["id"] for item in targets))

    def test_public_instance_masks_every_webhook_url(self):
        first = manager.instances()[0]
        self.add_webhook(first["id"], "One", "https://example.com/one")
        self.add_webhook(first["id"], "Two", "https://example.com/two")

        public = manager.public_instance(manager.get_instance(first["id"]))

        self.assertEqual([item["url"] for item in public["webhooks"]], ["********", "********"])

    def test_removed_instance_summary_omits_webhook_secrets(self):
        first = manager.instances()[0]
        self.add_webhook(first["id"], "One", "https://example.com/secret")

        public = manager.public_removed_instance(manager.get_instance(first["id"]))

        self.assertNotIn("webhook", public)
        self.assertNotIn("webhooks", public)

    def test_unknown_webhook_id_cannot_create_or_modify_an_entry(self):
        first = manager.instances()[0]

        with self.assertRaises(FileNotFoundError):
            manager.save_instance_webhook(first["id"], {"id": "not-on-this-server", "enabled": False})

        self.assertEqual(manager.get_instance(first["id"])["webhooks"], [])

    def test_webhook_can_be_deleted_from_only_its_server(self):
        first, second = manager.instances()
        first_webhook = self.add_webhook(first["id"], "First", "https://example.com/first")
        second_webhook = self.add_webhook(second["id"], "Second", "https://example.com/second")

        manager.delete_instance_webhook(first["id"], first_webhook["id"])

        self.assertEqual(manager.get_instance(first["id"])["webhooks"], [])
        self.assertEqual(manager.get_instance(second["id"])["webhooks"][0]["id"], second_webhook["id"])


if __name__ == "__main__":
    unittest.main()
