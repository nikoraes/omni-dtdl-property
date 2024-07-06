from copy import copy
from glob import glob
import json
from omni.kit.property.usd.usd_property_widget import (
    UsdPropertiesWidget,
    UsdPropertyUiEntry,
)
import carb
import carb.settings
import omni.ui as ui
import omni.kit.app
import omni.usd
from pxr import Usd, Sdf, Vt, Gf, UsdGeom, Trace
from dtdl.property.dtdl_model_modelrepo import DtdlExtendedModelData, DtdlProperty


class DtdlAttributeWidget(UsdPropertiesWidget):

    MODEL_ID_ATTR_NAME = "dtdl:modelId"
    DTDL_PATH_SETTING = "/persistent/exts/dtdl.property/dtdlPath"

    def __init__(self):
        super().__init__(title="DTDL", collapsed=False)

        self._model_repo: dict[str, DtdlExtendedModelData] = {}
        self._dtdl_property_list: list[DtdlProperty] = []
        # self._noplaceholder_list: dict[str, bool] = {}

        self._init_settings()
        self._read_settings()

        self._load_dtdl_model_repo()

    def _init_settings(self):
        self._dtdl_path = omni.kit.app.SettingChangeSubscription(
            DtdlAttributeWidget.DTDL_PATH_SETTING,
            lambda *_: self._on_settings_change(),
        )

    def _read_settings(self):
        settings = carb.settings.get_settings()
        # self._dtdl_path = settings.get(DTDL_PATH_SETTING)
        # TODO add some UI to settings
        self._dtdl_path = (
            "C:/Users/NRaes/Dev/omni/dtdl-property/exts/dtdl.property/data/*.json"
        )

    def _on_settings_change(self):
        self._read_settings()
        self.request_rebuild()

    def _load_dtdl_model_repo(self):
        """
        load all the DTDL models from the specified folder
        """
        self._model_repo = {}
        models = []
        # recursively load all the models from the folder
        # TODO: use omniverse file reader, so we can also support nucleus paths
        for file in glob(
            self._dtdl_path,
            recursive=True,
        ):
            with open(file) as f:
                model_json = json.load(f)
                if (
                    "@context" in model_json
                    and "@id" in model_json
                    and "@type" in model_json
                    and model_json["@type"] == "Interface"
                ):
                    models.append(model_json)
        # Generate all extended model data and store it in a dictionary
        for model in models:
            self._model_repo[model["@id"]] = DtdlExtendedModelData(model, models)

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
        prims = []
        for prim_path in self._payload:
            prim = self._get_prim(prim_path)
            if not prim or not (prim.IsA(UsdGeom.Xform) or prim.IsA(UsdGeom.Mesh)):
                return False
            prims.append(prim)

        # if model repo not loaded, don't show
        if self._model_repo is None:
            return False

        # get list of attributes and build a dictonary to make logic simpler later
        self._dtdl_property_list = []
        # self._noplaceholder_list = {}

        for prim in prims:
            model_id_attr = prim.GetAttribute(DtdlAttributeWidget.MODEL_ID_ATTR_NAME)
            if model_id_attr:
                # self._noplaceholder_list[DtdlAttributeWidget.MODEL_ID_ATTR_NAME] = True
                model_id = model_id_attr.Get()
                if model_id:
                    if model_id in self._model_repo:
                        model_data = self._model_repo[model_id]
                        self._dtdl_property_list = model_data.properties
                        # for prop in model_data.properties:
                        #     if prim.GetAttribute(prop.id):
                        #         self._noplaceholder_list[prop.id] = True

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

        # As these attributes are not part of the schema, placeholders need to be added. These are not
        # part of the prim until the value is changed. They will be added via prim.CreateAttribute(
        # This is also the reason for _placeholer_list as we don't want to add placeholders if valid
        # attribute already exists

        # Add the model Id attribute placeholder if it doesn't exist yet
        # if DtdlAttributeWidget.MODEL_ID_ATTR_NAME not in self._noplaceholder_list:
        attrs.append(
            UsdPropertyUiEntry(
                DtdlAttributeWidget.MODEL_ID_ATTR_NAME,
                "Model",
                {
                    Sdf.PrimSpec.TypeNameKey: "token",
                    "allowedTokens": Vt.TokenArray(
                        3,
                        ("", "dtmi:com:example:test;1", "dtmi:com:example:test;2"),
                    ),
                    "customData": {"default": ""},
                },
                Usd.Attribute,
            )
        )

        # Add all attributes for the models for the selected prims
        for prop in self._dtdl_property_list:
            attrs.append(prop.to_usd_property_ui_entry())
            # if prop.id not in self._noplaceholder_list:

        # remove any unwanted attrs (all of the Xform & Mesh
        # attributes as we don't want to display them in the widget)
        for attr in copy(attrs):
            if (attr.attr_name is not DtdlAttributeWidget.MODEL_ID_ATTR_NAME) and (
                attr.attr_name not in [p.id for p in self._dtdl_property_list]
            ):
                attrs.remove(attr)

        # custom UI attributes
        frame = CustomLayoutFrame(hide_extra=False)
        with frame:
            CustomLayoutProperty(DtdlAttributeWidget.MODEL_ID_ATTR_NAME, "Model")
            for prop in self._dtdl_property_list:
                prop.to_custom_layout_property()

        return frame.apply(attrs)

    @Trace.TraceFunction
    def _on_usd_changed(self, notice, stage):
        """
        called when UsdPropertiesWidget needs to inform of a property change
        NOTE: This is a Tf.Notice.Register(Usd.Notice.ObjectsChanged) callback, so is time sensitive function
              Keep code in this function to a minimum as heavy work can slow down kit
        """
        if stage != self._payload.get_stage():
            return

        self._dtdl_property_list = []

        super()._on_usd_changed(notice=notice, stage=stage)

        # check for attribute changed or created by +add menu as widget refresh is required
        for path in notice.GetChangedInfoOnlyPaths():
            if path.name is DtdlAttributeWidget.MODEL_ID_ATTR_NAME:
                self.request_rebuild()

        # self.request_rebuild()
        # self.build_items()
        # self.request_rebuild()

        #         print("Model ID changed")
        #         self._dtdl_property_list = []
        #         # self._noplaceholder_list = {}
        #         prims = []
        #         for prim_path in self._payload:
        #             prim = self._get_prim(prim_path)
        #             if not prim or not (
        #                 prim.IsA(UsdGeom.Xform) or prim.IsA(UsdGeom.Mesh)
        #             ):
        #                 return False
        #             prims.append(prim)
        #         for prim in prims:
        #             model_id_attr = prim.GetAttribute(
        #                 DtdlAttributeWidget.MODEL_ID_ATTR_NAME
        #             )
        #             if model_id_attr:
        #                 # self._noplaceholder_list[DtdlAttributeWidget.MODEL_ID_ATTR_NAME] = True
        #                 model_id = model_id_attr.Get()
        #                 if model_id:
        #                     if model_id in self._model_repo:
        #                         model_data = self._model_repo[model_id]
        #                         self._dtdl_property_list = model_data.properties
        #         # self.reset()
        #         # self.build_items()
        #         self.request_rebuild()
        #         # self.build_impl()
