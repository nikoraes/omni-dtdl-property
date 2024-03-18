from typing import List

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
        self.bases: List[str] = []
        self.properties: List[UsdPropertyUiEntry] = []

    def _add_model_contents_recursive(self, model_id: str, all_models: list[object]):
        model = next(m for m in all_models if m["@id"] == model_id)
        self._model_repo[model["@id"]] = {["model"]: model, ["properties"]: []}
        if "contents" in model:
            if model["contents"] is object:
                model["contents"] = [model["contents"]]
            for c in model["contents"]:
                if c["@type"] == "Property" or "Property" in c["@type"]:
                    self._model_repo[model["@id"]]["properties"].append(c)
        if "extends" in model:
            if isinstance(model["extends"], list):
                for base in model["extends"]:
                    self._add_model_contents_recursive(base, all_models)
            else:
                self._add_model_contents_recursive(model["extends"], all_models)

    def _usd_property_from_dtdl_property(
        self, dtdl_property: object, modelId: str
    ) -> UsdPropertyUiEntry:
        id: str = dtdl_property["@id"] if "@id" in dtdl_property else ""
        return UsdPropertyUiEntry(
            "dtmi:com:arcadis:test:boolean",
            "",
            {
                Sdf.PrimSpec.TypeNameKey: "bool",
                "customData": {"default": False},
            },
            Usd.Attribute,
        )


class DtdlModelRepository:
    """
    Stores the USD attribute definitions per DTDL model for easy retrieval
    """

    def __init__(self, models: list[object]):
        self._model_repo: dict[str, list[UsdPropertyUiEntry]] = []
