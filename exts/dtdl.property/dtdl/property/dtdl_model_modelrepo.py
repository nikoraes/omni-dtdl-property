from pxr import Usd, Sdf
from omni.kit.property.usd.usd_property_widget import UsdPropertyUiEntry


class DtdlProperty:

    def __init__(self, name: str, display_name: str, schema: str, comment: str):
        self.name = name
        self.display_name = display_name
        self.schema = schema

    def from_dict(self, data: dict):
        self.name = data["name"]
        self.display_name = data["displayName"]
        self.schema = data["schema"]
        self.comment = data["comment"]
        return self


class DtdlExtendedModelData:
    def __init__(self, model: object, all_models: list[object]):
        self.model = model
        self.bases: list[str] = []
        self.properties: list[UsdPropertyUiEntry] = []
        self._add_model_contents_recursive(model["@id"], all_models)

    def _add_model_contents_recursive(self, model_id: str, all_models: list[object]):
        model = next(m for m in all_models if m["@id"] == model_id)
        if "contents" in model:
            if model["contents"] is object:
                model["contents"] = [model["contents"]]
            for c in model["contents"]:
                if c["@type"] == "Property" or "Property" in c["@type"]:
                    property_entry = self._usd_property_from_dtdl_property(c, model_id)
                    self.properties.append(property_entry)
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

    def _usd_property_from_dtdl_property(
        self, dtdl_property: object, modelId: str
    ) -> UsdPropertyUiEntry:
        id: str = (
            dtdl_property["@id"]
            if "@id" in dtdl_property
            else "{}:_contents:{};{}".format(
                modelId.split(";")[0], dtdl_property["name"], modelId.split(";")[1]
            )
        )
        displayName: str = (
            (
                dtdl_property["displayName"]["en"]
                if "en" in dtdl_property["displayName"]
                else dtdl_property["displayName"]
            )
            if "displayName" in dtdl_property
            else dtdl_property["name"]
        )
        return UsdPropertyUiEntry(
            id,
            displayName,
            {
                Sdf.PrimSpec.TypeNameKey: "bool",
            },
            Usd.Attribute,
        )
