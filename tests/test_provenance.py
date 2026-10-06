"""Provenance: imported configuration is marked, and marked again once edited here.

The UI colours profiles, labware, liquid classes and accessories by origin:
"registry_import" (from a registry export, unchanged), "registry_import_modified"
(imported, then edited in pyBravo) or local.
"""
from __future__ import annotations

import os
import time

import yaml

from pybravo import labware_editor, liquid_classes
from pybravo.deck.labware import LabwareDefinition
from pybravo.profile.profile import BravoProfile
from pybravo.profile.reg_import import reg_to_profile
from pybravo.web import server

REG = (
    "Windows Registry Editor Version 5.00\n\n"
    "[HKEY_LOCAL_MACHINE\\SOFTWARE\\WOW6432Node\\Velocity11\\Bravo2\\Profiles\\Lab Bravo]\n"
    '"Approach height"="10"\n'
)


def test_registry_import_records_its_origin_and_survives_a_save(tmp_path):
    profile, _ = reg_to_profile(REG)
    origin = profile.extra["origin"]
    assert origin["kind"] == "registry_import"
    assert origin["source_name"] == "Lab Bravo"
    assert origin["imported_at"]

    path = tmp_path / "lab.yaml"
    profile.save(path)
    assert BravoProfile.load(path).extra["origin"]["kind"] == "registry_import"


def test_profile_origin_tells_imported_edited_and_local_apart(tmp_path):
    profile, _ = reg_to_profile(REG)
    imported = tmp_path / "imported.yaml"
    profile.save(imported)
    assert server._profile_origin(imported) == "registry_import"

    later = time.time() + 60
    os.utime(imported, (later, later))  # saved again well after the import
    assert server._profile_origin(imported) == "registry_import_modified"

    local = tmp_path / "local.yaml"
    BravoProfile.default().save(local)
    assert server._profile_origin(local) == "local"


def test_labware_origin_round_trips_and_an_edit_marks_it(tmp_path, monkeypatch):
    monkeypatch.setenv("PYBRAVO_LABWARE_EDITOR_PATH", str(tmp_path / "editor.yaml"))
    monkeypatch.setenv("PYBRAVO_LABWARE_SNAPSHOT_PATH", str(tmp_path / "snapshot.yaml"))
    definition = LabwareDefinition(id="lw-1", name="Imported Plate", kind="sbs_plate", wells=96,
                                   origin="registry_import")

    item = labware_editor._definition_to_editor_type(definition)
    assert labware_editor._editor_type_to_definition(item).origin == "registry_import"

    labware_editor.save_store({"version": 1, "labware_types": [item], "labware_classes": []})
    edited = labware_editor.patch_type("lw-1", {"description": "changed here"})
    assert edited["origin"] == "registry_import_modified"

    snapshot = yaml.safe_load((tmp_path / "snapshot.yaml").read_text(encoding="utf-8"))
    assert snapshot["labware"][0]["origin"] == "registry_import_modified"


def test_liquid_class_edit_marks_an_imported_class(tmp_path, monkeypatch):
    monkeypatch.setenv("PYBRAVO_LIQUID_CLASS_STORE_PATH", str(tmp_path / "liquid.yaml"))
    created = liquid_classes.create_liquid_class({
        "name": "Water", "machine_id": "SIM_BRAVO", "head_type": "HT_96_D_70",
        "tip_capacity_ul": 70, "origin": "registry_import",
    })
    assert created["origin"] == "registry_import"

    edited = liquid_classes.patch_liquid_class(created["liquid_class_id"], {"description": "tuned"})
    assert edited["origin"] == "registry_import_modified"

    local = liquid_classes.create_liquid_class({
        "name": "Buffer", "machine_id": "SIM_BRAVO", "head_type": "HT_96_D_70", "tip_capacity_ul": 70,
    })
    assert local["origin"] == ""
