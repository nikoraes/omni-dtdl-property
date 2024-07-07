from typing import Callable
import carb.settings
import omni.ui as ui
import omni.kit.app
from os import path
from omni.kit.window.preferences import PreferenceBuilder, SettingType
from .dtdl_property_extension import DTDL_PATH_SETTING, DTDL_PATH_SETTING_ID


class DtdlPropertyPreferences(PreferenceBuilder):
    """Preferences page for the DTDL Property extension"""

    def __init__(self):
        super().__init__("Property Widgets")
        self._settings = carb.settings.get_settings()
        self._set_default_settings()
        self._dtdl_path_setting_widget = None

    def build(self):
        """Build the preferences page"""
        with ui.VStack(height=0):
            with self.add_frame("DTDL Properties"):
                with ui.VStack():
                    self._dtdl_path_setting_widget = self.create_setting_widget(
                        "Path to DTDL models\n\n",
                        DTDL_PATH_SETTING,
                        SettingType.STRING,
                        clicked_fn=self._on_browse_button_fn,
                    )
                    self._dtdl_path_setting_widget.identifier = DTDL_PATH_SETTING_ID

    def _set_default_settings(self):
        """Setup default value for the extension settings"""
        manager = omni.kit.app.get_app().get_extension_manager()
        manager.get_extension_dict
        ext_path = path.normpath(manager.get_extension_path_by_module("dtdl.property"))
        self.dtdl_path = path.join(ext_path, "data")
        self._settings.set_default_string(DTDL_PATH_SETTING, self.dtdl_path)

        current_dtdl_path = self._settings.get_as_string(DTDL_PATH_SETTING)
        if current_dtdl_path is not None and current_dtdl_path != "":
            return
        self._settings.set_string(DTDL_PATH_SETTING, self.dtdl_path)

    def _on_browse_button_fn(self, owner):
        """Called when the user picks the Browse button."""
        path = self._dtdl_path_setting_widget.model.get_value_as_string()

        from functools import partial
        from omni.kit.window.file_importer import get_file_importer

        def on_import(click_fn: Callable, filename: str, dirname: str, selections=[]):
            dirname = dirname.strip()
            if dirname and not dirname.endswith("/"):
                dirname += "/"
            fullpath = f"{dirname}"
            if click_fn:
                click_fn(fullpath)

        file_importer = get_file_importer()
        if file_importer:
            file_importer.show_window(
                title="Select Folder",
                import_button_label="Select",
                import_handler=partial(on_import, self._on_file_pick),
                filename_url=path,
                file_extension_types=[("All Folders(*)", "")],
                show_only_folders=True,
            )

    def _on_file_pick(self, full_path):
        """Called when the user accepts directory in the Select Directory dialog."""

        normalized_path = path.normpath(full_path)

        self._settings.set(
            DTDL_PATH_SETTING,
            normalized_path,
        )
        self._dtdl_path_setting_widget.model.set_value(normalized_path)
