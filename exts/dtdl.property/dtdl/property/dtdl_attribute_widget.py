from copy import copy
from omni.kit.property.usd.usd_property_widget import (
    UsdPropertiesWidget,
    UsdPropertyUiEntry,
)
import carb
import omni.ui as ui
import omni.usd
from pxr import Usd, Sdf, Vt, Gf, UsdGeom, Trace
from dtdl.property.dtdl_model_modelrepo import DtdlExtendedModelData, DtdlProperty

model_id_attr_name = "dtdl:modelId"


class DtdlAttributeWidget(UsdPropertiesWidget):

    def __init__(self, model_repo: dict[str, DtdlExtendedModelData]):
        super().__init__(title="DTDL", collapsed=False)
        self._model_repo = model_repo
        self._attribute_list: list[DtdlProperty] = []

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

        # get list of attributes and build a dictonary to make logic simpler later
        self._attribute_list = []
        for prim in prims:
            model_id_attr = prim.GetAttribute(model_id_attr_name)
            model_id = model_id_attr.Get()
            if model_id:
                if model_id in self._model_repo:
                    model_data = self._model_repo[model_id]
                    for prop in model_data.properties:
                        if not any(p.id == prop.id for p in self._attribute_list):
                            self._attribute_list.append(prop)

        return True

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
            CustomLayoutGroup,
            CustomLayoutProperty,
        )
        from omni.kit.property.usd.usd_property_widget_builder import (
            UsdPropertiesWidgetBuilder,
        )
        from omni.kit.window.property.templates import (
            HORIZONTAL_SPACING,
            LABEL_HEIGHT,
            LABEL_WIDTH,
        )

        # As these attributes are not part of the schema, placeholders need to be added. These are not
        # part of the prim until the value is changed. They will be added via prim.CreateAttribute(
        # This is also the reason for _placeholer_list as we don't want to add placeholders if valid
        # attribute already exists

        # Add the model Id attribute
        attrs.append(
            UsdPropertyUiEntry(
                model_id_attr_name,
                "Model",
                {Sdf.PrimSpec.TypeNameKey: "string"},
                Usd.Attribute,
            )
        )

        # Add all attributes for the models for the selected prims
        for prop in self._attribute_list:
            attrs.append(prop.to_usd_property_ui_entry())

        # remove any unwanted attrs (all of the Xform & Mesh
        # attributes as we don't want to display them in the widget)
        for attr in copy(attrs):
            if (attr.attr_name is not model_id_attr_name) and (
                attr.attr_name not in [p.id for p in self._attribute_list]
            ):
                attrs.remove(attr)

        # custom UI attributes
        frame = CustomLayoutFrame(hide_extra=False)
        with frame:
            CustomLayoutProperty(model_id_attr_name, "Model")
            for prop in self._attribute_list:
                prop.to_custom_layout_property()

        return frame.apply(attrs)
