from pxr import Usd, Sdf
from omni.kit.property.usd.custom_layout_helper import CustomLayoutProperty
from omni.kit.property.usd.usd_property_widget import UsdPropertyUiEntry


class DtdlProperty:

    def __init__(self, data: dict, model_id: str):
        # The property id is used as attr_name in the USD schema
        self.id = "dtdl:{}".format(data["name"])
        self.name = data["name"]
        self.display_name = (
            (
                data["displayName"]["en"]
                if "en" in data["displayName"]
                else data["displayName"]
            )
            if "displayName" in data
            else data["name"]
        )
        self.description = (
            (
                data["description"]["en"]
                if "en" in data["description"]
                else data["description"]
            )
            if "description" in data
            else None
        )
        self.schema = data["schema"]

    def to_custom_layout_property(self):
        return CustomLayoutProperty(self.id, self.display_name)

    def to_usd_property_ui_entry(self):
        # TODO: enum, object, ...
        return UsdPropertyUiEntry(
            self.id,
            "Properties",
            {
                Sdf.PrimSpec.TypeNameKey: dtdl_schema_to_usd_schema(self.schema),
                Sdf.PrimSpec.DocumentationKey: {
                    "documentation": self.description,
                },
            },
            Usd.Attribute,
        )


def dtdl_schema_to_usd_schema(dtdl_schema: str) -> str:
    match dtdl_schema:
        case "boolean":
            return "bool"
        case "integer":
            return "int"
        case "long":
            return "int64"
        case _:
            return dtdl_schema


class DtdlExtendedModelData:
    def __init__(self, model: object, all_models: list[object]):
        self.model = model
        self.bases: list[str] = []
        self.properties: list[DtdlProperty] = []  # todo add typing
        self._add_model_contents_recursive(model["@id"], all_models)

    def _add_model_contents_recursive(
        self, model_id: str, all_models: list[DtdlProperty]
    ):
        model = next(m for m in all_models if m["@id"] == model_id)
        if "contents" in model:
            if model["contents"] is object:
                model["contents"] = [model["contents"]]
            for c in model["contents"]:
                if c["@type"] == "Property" or "Property" in c["@type"]:
                    self.properties.append(DtdlProperty(c, model_id))
        if "extends" in model:
            if isinstance(model["extends"], list):
                for base in model["extends"]:
                    if base not in self.bases:
                        self.bases.append(base)
                    self._add_model_contents_recursive(base, all_models)
            else:
                if model["extends"] not in self.bases:
                    self.bases.append(model["extends"])
                self._add_model_contents_recursive(model["extends"], all_models)
