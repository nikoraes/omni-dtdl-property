import json
import time
import threading
from os import path
import carb
import carb.settings
import omni.client
import omni.kit.app
import omni.usd
from omni.kit.property.usd.usd_property_widget import (
    UsdPropertiesWidget,
    UsdPropertyUiEntry,
)
from pxr import Usd, Sdf, Vt, UsdGeom, Trace
from .dtdl_model_modelrepo import DtdlExtendedModelData, DtdlContent
from .dtdl_property_extension import DTDL_PATH_SETTING, MODEL_ID_ATTR_NAME


class DtdlAttributeWidget(UsdPropertiesWidget):
    """Widget to display DTDL properties in the property window"""

    def __init__(self):
        super().__init__(title="DTDL", collapsed=False)
        self._dtdl_path: str = None
        self._subscribe_settings()
        self._read_settings()

        self._dtdl_model_repo: dict[str, DtdlExtendedModelData] = {}
        self._dtdl_contents_list: list[DtdlContent] = []
        # self._noplaceholder_list: dict[str, bool] = {}

        # holds the file entries, but not the absolute path
        # self._dtdl_file_list: list[omni.client.ListEntry] = []
        # holds the absolute path to the files
        # self._dtdl_file_urls: list[str] = []
        (self._dtdl_file_list, self._dtdl_file_urls) = self._get_dtdl_file_list()
        self._load_dtdl_model_repo()

        self._stop_event = threading.Event()
        # Start the dtdl folder watcher in a separate thread
        self._dtdl_watcher_thread = threading.Thread(target=self._watch_dtdl_path)
        self._dtdl_watcher_thread.start()
        # Settings subscription
        self._setting_sub

    def __del__(self):
        self._stop_watching()

    def _subscribe_settings(self):
        """Subscribe to settings changes to reload the DTDL models when the path changes"""

        def on_change():
            self._on_settings_change()

        self._setting_sub = (
            carb.settings.get_settings().subscribe_to_node_change_events(
                DTDL_PATH_SETTING, on_change
            )
        )
        # self._dtdl_path = omni.kit.app.SettingChangeSubscription(
        #     DTDL_PATH_SETTING,
        #     self._on_settings_change,
        # )
        # TODO: This isn't triggering ... figure out why

    def _read_settings(self):
        """Read the settings to get the path to the DTDL models"""
        settings = carb.settings.get_settings()
        self._dtdl_path = settings.get(DTDL_PATH_SETTING)

    def _on_settings_change(self):
        """Called when the settings change"""
        self._read_settings()
        self.request_rebuild()

    def _stop_watching(self):
        """Stop the dtdl folder watcher thread"""
        self._stop_event.set()
        self._dtdl_watcher_thread.join()
        """Stop the settings change subscription"""
        carb.settings.get_settings().unsubscribe_to_change_events(self._setting_sub)

    def _get_dtdl_file_list(self):
        # the file entries, but not the absolute path
        dtdl_file_list: list[omni.client.ListEntry] = []
        # the absolute path to the files
        dtdl_file_urls: list[str] = []

        def recursive_list_files(folder):
            (result, file_list) = omni.client.list(folder)
            for list_entry in file_list:
                if (list_entry.flags & omni.client.ItemFlags.READABLE_FILE) and (
                    list_entry.relative_path.endswith(".json")
                ):
                    dtdl_file_list.append(list_entry)
                    dtdl_file_urls.append(path.join(folder, list_entry.relative_path))
                elif list_entry.flags & omni.client.ItemFlags.CAN_HAVE_CHILDREN:
                    recursive_list_files(path.join(folder, list_entry.relative_path))

        recursive_list_files(self._dtdl_path)

        return (dtdl_file_list, dtdl_file_urls)

    def _watch_dtdl_path(self):
        """
        Watch the DTDL path for changes by periodically checking the filtered list
        of files and their updated timestamps in the folder
        """
        while not self._stop_event.is_set():
            # (result, full_file_list) = omni.client.list(self._dtdl_path)
            # file_list = [
            #     entry for entry in full_file_list if ".json" in entry.relative_path
            # ]
            (file_list, file_urls) = self._get_dtdl_file_list()
            if len(self._dtdl_file_list) == 0:
                self._dtdl_file_list = file_list
                self._dtdl_file_urls = file_urls
                self._load_dtdl_model_repo()
                time.sleep(20)
                continue
            new_files = [
                list_entry
                for list_entry in file_list
                if list_entry.relative_path
                not in [entry.relative_path for entry in self._dtdl_file_list]
            ]
            deleted_files = [
                entry
                for entry in self._dtdl_file_list
                if entry.relative_path
                not in [list_entry.relative_path for list_entry in file_list]
            ]
            if len(new_files) > 0 or len(deleted_files) > 0:
                self._dtdl_file_list = file_list
                self._dtdl_file_urls = file_urls
                self._load_dtdl_model_repo()
                time.sleep(20)
                continue
            for list_entry in new_files:
                modified_time = list_entry.modified_time
                existing_entry = next(
                    entry
                    for entry in self._dtdl_file_list
                    if entry.relative_path == list_entry.relative_path
                )
                if modified_time > existing_entry.modified_time:
                    self._dtdl_file_list = file_list
                    self._dtdl_file_urls = file_urls
                    self._load_dtdl_model_repo()
                    time.sleep(20)
                    continue
            time.sleep(10)

    def _set_modelid_allowed_tokens(self):
        """
        When the model repo changes, we need to traverse all prims that have the dtdm:modelId attribute
        and update the allowed tokens for the attribute
        """
        # Prepare allowed tokens Tuple
        allowed_tokens = Vt.TokenArray(
            len(self._dtdl_model_repo) + 1,
            ("", *self._dtdl_model_repo.keys()),
        )
        # Get current stage
        usd_context = omni.usd.get_context()
        stage = usd_context.get_stage()
        # Traverse all prims in the stage
        for prim in stage.Traverse():
            # Get the model id attribute
            model_id_attr = prim.GetAttribute(MODEL_ID_ATTR_NAME)
            current_allowed_tokens = model_id_attr.GetMetadata("allowedTokens")
            if current_allowed_tokens is not None:
                model_id_attr.SetMetadata("allowedTokens", allowed_tokens)
                # v = model_id_attr.Get()
                # allowed_tokens = model_id_attr.GetMetadata("allowedTokens")
                # # n = model_id_attr.GetAllMetadata()
                # # o = model_id_attr.GetCustomData()
                # # Set the allowed tokens
                # model_id_attr.Get()

    def _load_dtdl_model_repo(self):
        """
        Load all the DTDL models from the specified folder. All (extended) models are stored in a dictionary
        with the model id as the key. The extended model data also includes the properties of the super classes.
        """
        self._dtdl_model_repo = {}
        models = []

        for file_url in self._dtdl_file_urls:
            (result, version, content) = omni.client.read_file(file_url)
            model_json = json.loads(memoryview(content).tobytes())
            if isinstance(model_json, dict):
                if (
                    "@context" in model_json
                    and "@id" in model_json
                    and "@type" in model_json
                    and model_json["@type"] == "Interface"
                ):
                    models.append(model_json)
            # if the json is an array, we need to iterate over the array
            elif isinstance(model_json, list):
                for model in model_json:
                    if (
                        "@context" in model
                        and "@id" in model
                        and "@type" in model
                        and model["@type"] == "Interface"
                    ):
                        models.append(model)
        # Generate all extended model data and store it in a dictionary
        for model in models:
            self._dtdl_model_repo[model["@id"]] = DtdlExtendedModelData(model, models)
        # Rebuild the UI
        # prims = self._get_valid_prims()
        # self._build_dtdl_contents_list(prims)
        # self.request_rebuild()

        # Update the allowed tokens for the model id attribute in each prim
        self._set_modelid_allowed_tokens()

        return self._dtdl_model_repo

    def _get_valid_prims(self):
        """
        Get all the valid prims from the selected prims
        """
        prims = []
        if not self._payload:
            return prims
        for prim_path in self._payload:
            prim = self._get_prim(prim_path)
            if prim and (prim.IsA(UsdGeom.Xform) or prim.IsA(UsdGeom.Mesh)):
                prims.append(prim)
        return prims

    def _build_dtdl_contents_list(self, prims):
        """
        Build a list of DTDL properties for the selected prims
        """
        self._dtdl_contents_list = []
        for prim in prims:
            model_id_attr = prim.GetAttribute(MODEL_ID_ATTR_NAME)
            if model_id_attr:
                model_id = model_id_attr.Get()
                if model_id:
                    if model_id in self._dtdl_model_repo:
                        model_data = self._dtdl_model_repo[model_id]
                        for prop in model_data.properties:
                            if prop.id not in [p.id for p in self._dtdl_contents_list]:
                                self._dtdl_contents_list.append(prop)
                        for telemetry in model_data.telemetries:
                            if telemetry.id not in [
                                p.id for p in self._dtdl_contents_list
                            ]:
                                self._dtdl_contents_list.append(telemetry)
                        for rel in model_data.relationships:
                            if rel.id not in [p.id for p in self._dtdl_contents_list]:
                                self._dtdl_contents_list.append(rel)

        return self._dtdl_contents_list

    def on_new_payload(self, payload):
        """
        Called when a new payload is delivered. PropertyWidget can take this opportunity to update its ui models,
        or schedule full UI rebuild.

        Args:
            payload: The new payload to refresh UI or update model.

        Return:
            True if the UI needs to be rebuilt. build_impl will be called as a result.
            False if the UI does not need to be rebuilt. build_impl will not be called.
        """

        # nothing selected, so do not show widget. If you don't do this
        # you widget will be always on, like the path widget you see
        # at the top.
        if not payload or len(payload) == 0:
            return False

        # filter out special cases like large number of prim selected. As
        # this can cause UI stalls in certain cases
        if not super().on_new_payload(payload):
            return False

        # check is all selected prims are relevent class/types
        prims = self._get_valid_prims()

        # if model repo not loaded, don't show
        if self._dtdl_model_repo is None:
            return False

        self._build_dtdl_contents_list(prims)

        return payload is not None and len(payload) > 0

    def _customize_props_layout(self, attrs):
        """
        This will generate the UI based on the provided attributes.

        NOTE: All above changes won't go back to USD, they're pure UI overrides.

        Args:
            props: List of Tuple(property_name, property_group, metadata)

        Example:

            for prop in props:
                # Change display group:
                prop.override_display_group("New Display Group")

                # Change display name (you can change other metadata, it won't be write back to USD, only affect UI):
                prop.override_display_name("New Display Name")

            # add additional "property" that doesn't exist.
            props.append(UsdPropertyUiEntry("PlaceHolder", "Group", { Sdf.PrimSpec.TypeNameKey: "bool"}, Usd.Property))
        """
        from omni.kit.property.usd.custom_layout_helper import (
            CustomLayoutFrame,
            CustomLayoutProperty,
        )

        ui_entries = []

        # As these attributes are not part of the schema, placeholders need to be added. These are not
        # part of the prim until the value is changed. They will be added via prim.CreateAttribute(
        # This is also the reason for _placeholer_list as we don't want to add placeholders if valid
        # attribute already exists

        # Add the model Id attribute placeholder if it doesn't exist yet
        # if MODEL_ID_ATTR_NAME not in self._noplaceholder_list:
        ui_entries.append(
            UsdPropertyUiEntry(
                MODEL_ID_ATTR_NAME,
                "Model",
                {
                    Sdf.PrimSpec.TypeNameKey: "token",
                    "allowedTokens": Vt.TokenArray(
                        len(self._dtdl_model_repo) + 1,
                        ("", *self._dtdl_model_repo.keys()),
                    ),
                    "customData": {"default": ""},
                },
                Usd.Attribute,
            )
        )

        # Add all attributes for the models for the selected prims
        for prop in self._dtdl_contents_list:
            ui_entries.append(prop.to_usd_property_ui_entry())
            # if prop.id not in self._noplaceholder_list:

        # remove any unwanted attrs (all of the Xform & Mesh
        # attributes as we don't want to display them in the widget)
        # for attr in copy(attrs):
        #     if (attr.attr_name is not MODEL_ID_ATTR_NAME) and (
        #         attr.attr_name not in [p.id for p in self._dtdl_contents_list]
        #     ):
        #         attrs.remove(attr)

        # custom UI attributes
        frame = CustomLayoutFrame(hide_extra=False)
        with frame:
            CustomLayoutProperty(MODEL_ID_ATTR_NAME, "Model")
            for prop in self._dtdl_contents_list:
                prop.to_custom_layout_property()

        return frame.apply(ui_entries)

    @Trace.TraceFunction
    def _on_usd_changed(self, notice, stage):
        """
        called when UsdPropertiesWidget needs to inform of a property change
        NOTE: This is a Tf.Notice.Register(Usd.Notice.ObjectsChanged) callback, so is time sensitive function
              Keep code in this function to a minimum as heavy work can slow down kit
        """
        if stage != self._payload.get_stage():
            return

        super()._on_usd_changed(notice=notice, stage=stage)

        # check for attribute changed or created by +add menu as widget refresh is required
        paths = notice.GetChangedInfoOnlyPaths()
        if MODEL_ID_ATTR_NAME in [p.name for p in paths]:
            prims = self._get_valid_prims()
            self._build_dtdl_contents_list(prims)
            self.request_rebuild()
