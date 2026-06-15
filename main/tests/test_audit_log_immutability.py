# -*- coding: utf-8 -*-
from django.core.exceptions import ValidationError
from django.test import TestCase

from main.models import AuditLog


class AuditLogImmutabilityTest(TestCase):
    def test_audit_log_cannot_be_updated_after_insert(self):
        log = AuditLog.objects.create(
            action=AuditLog.Action.CREATE,
            module="test",
            model_name="Dummy",
            object_id="1",
            changes={"before": None, "after": "created"},
        )
        log.note = "tampered"
        with self.assertRaises(ValidationError):
            log.save(update_fields=["note"])

    def test_audit_log_delete_is_blocked(self):
        log = AuditLog.objects.create(
            action=AuditLog.Action.CREATE,
            module="main",
            model_name="AuditLog",
            object_id="delete-blocked",
            changes={"ok": True},
        )
        with self.assertRaises(ValidationError):
            log.delete()
        self.assertTrue(AuditLog.objects.filter(pk=log.pk).exists())

    def test_audit_log_queryset_update_is_blocked(self):
        log = AuditLog.objects.create(
            action=AuditLog.Action.UPDATE,
            module="main",
            model_name="AuditLog",
            object_id="bulk-update-blocked",
            changes={"ok": True},
        )
        with self.assertRaises(ValidationError):
            AuditLog.objects.filter(pk=log.pk).update(note="tampered")
        log.refresh_from_db()
        self.assertNotEqual(log.note, "tampered")

    def test_audit_log_queryset_delete_is_blocked(self):
        log = AuditLog.objects.create(
            action=AuditLog.Action.DELETE,
            module="main",
            model_name="AuditLog",
            object_id="bulk-delete-blocked",
            changes={"ok": True},
        )
        with self.assertRaises(ValidationError):
            AuditLog.objects.filter(pk=log.pk).delete()
        self.assertTrue(AuditLog.objects.filter(pk=log.pk).exists())
