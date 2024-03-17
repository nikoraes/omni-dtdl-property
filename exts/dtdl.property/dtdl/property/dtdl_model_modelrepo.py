from typing import List


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
    def __init__(self, model: object):
        self.model = model

    bases: List[str] = []
    properties: List[DtdlProperty] = []


"""  // recursively add all properties (also from parent models)
  const addModelContents = (model: DtdlInterface, reset = true) => {
    // reset category order
    if (reset) resetCategoryOrder()
    if (model.contents) {
      // workaround for model definition with just 1 content defined as object instead of array
      if (!Array.isArray(model.contents) && typeof model.contents === "object") model.contents = [model.contents]
      contents.properties.unshift(...model.contents
        .filter((c): c is DtdlProperty => (c["@type"] === "Property" || c["@type"].includes("Property")) && !contents.properties.some(p => p.name === c.name))
        .map(p => replaceUriKeys(p)))
      // sort properties by commentOrder
      contents.properties.sort(compareCommentOrder)
      contents.relationships.unshift(...model.contents
        .filter((c): c is DtdlRelationship => c["@type"] === "Relationship" && !contents.relationships.some(p => p.name === c.name))
        .map(p => replaceUriKeys(p)))
      contents.telemetries.unshift(...model.contents
        .filter((c): c is DtdlTelemetry => (c["@type"] === "Telemetry" || c["@type"].includes("Telemetry")) && !contents.telemetries.some(p => p.name === c.name))
        .map(p => replaceUriKeys(p)))
      contents.components.unshift(...model.contents
        .filter((c): c is DtdlComponent => c["@type"] === "Component" && !contents.components.some(p => p.name === c.name))
        .map(p => replaceUriKeys(p)))
    }
    if (model.extends) {
      if (Array.isArray(model.extends)) {
        model.extends.forEach(x => {
          contents.bases.unshift(x)
          const baseModel = models.find(y => y.id === x)?.model
          if (baseModel) addModelContents(baseModel, false)
        })
      } else {
        contents.bases.unshift(model.extends)
        const baseModel = models.find(y => y.id === model.extends)?.model
        if (baseModel) addModelContents(baseModel, false)
      }
    }
  } """


class DtdlModelRepository:
    def __init__(self, models: List[object]):
        self._model_repo: dict[str, DtdlExtendedModelData] = []

    def _add_model_contents_recursive(self, model: object):
        self._model_repo[model["@id"]] = {["model"]: model, ["properties"]: []}
        if "contents" in model:
            if model["contents"] is object:
                model["contents"] = [model["contents"]]
            for c in model["contents"]:
                if c["@type"] == "Property" or "Property" in c["@type"]:
                    self._model_repo[model["@id"]]["properties"].append(c)

    def get_model(self, model_id: str) -> DtdlModel:
        return self._model_repo.get_model(model_id)

    def add_model(self, model: DtdlModel):
        self._model_repo.add_model(model)

    def get_properties(self, model_id: str) -> List[DtdlProperty]:
        return self._model_repo.get_properties(model_id)
