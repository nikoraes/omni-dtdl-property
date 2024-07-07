from abc import abstractmethod
from pxr import Usd, Sdf
from omni.kit.property.usd.custom_layout_helper import CustomLayoutProperty
from omni.kit.property.usd.usd_property_widget import UsdPropertyUiEntry


class DtdlContent:
    """Base class to represent a DTDL content in the model repository"""

    def __init__(self, data: dict):
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
        if "schema" in data:
            self.schema = data["schema"]

    def to_custom_layout_property(self):
        """Converts the property to a CustomLayoutProperty object for the property window"""
        return CustomLayoutProperty(self.id, self.display_name)

    @abstractmethod
    def to_usd_property_ui_entry(self):
        """Converts the property to a UsdPropertyUiEntry object for the USD schema"""
        pass


class DtdlProperty(DtdlContent):
    """Class to represent a DTDL property in the model repository"""

    def __init__(self, data: dict):
        super().__init__(data)

    def to_usd_property_ui_entry(self):
        """Converts the property to a UsdPropertyUiEntry object for the USD schema"""
        # TODO: enum, object, ...
        return UsdPropertyUiEntry(
            self.id,
            "Properties",
            {
                Sdf.PrimSpec.TypeNameKey: dtdl_primitive_schema_to_usd_schema(
                    self.schema
                ),
                Sdf.PrimSpec.DocumentationKey: self.description,
                "customData": {"default": _get_default_by_schema(self.schema)},
            },
            Usd.Attribute,
        )


class DtdlTelemetry(DtdlContent):
    """Class to represent a DTDL telemetry in the model repository"""

    def __init__(self, data: dict):
        super().__init__(data)

    def to_usd_property_ui_entry(self):
        """Converts the property to a UsdPropertyUiEntry object for the USD schema"""
        # TODO: enum, object, ...
        return UsdPropertyUiEntry(
            self.id,
            "Telemetry",
            {
                Sdf.PrimSpec.TypeNameKey: dtdl_primitive_schema_to_usd_schema(
                    self.schema
                ),
                Sdf.PrimSpec.DocumentationKey: self.description,
                "customData": {"default": _get_default_by_schema(self.schema)},
            },
            Usd.Attribute,
        )


class DtdlRelationship(DtdlContent):
    """Class to represent a DTDL relationship in the model repository"""

    def __init__(self, data: dict):
        super().__init__(data)

    def to_usd_property_ui_entry(self):
        """Converts the property to a UsdPropertyUiEntry object for the USD schema"""
        return UsdPropertyUiEntry(
            self.id,
            "Relationships",
            {
                Sdf.PrimSpec.DocumentationKey: self.description,
            },
            Usd.Relationship,
        )


def dtdl_primitive_schema_to_usd_schema(dtdl_schema: str) -> str:
    """
    Converts a DTDL schema to a USD schema. Only the primitive types are converted.
    As a fallback, it is assumed that the types align between DTDL and USD (e.g. "string" in DTDL
    is also "string" in USD).
    """
    match dtdl_schema:
        case "boolean":
            return "bool"
        case "integer":
            return "int"
        case "long":
            return "int64"
        case _:
            return dtdl_schema


def _get_default_by_schema(schema: str) -> str:
    """
    Get the default value for a given schema. This is used to set the default value in the USD
    schema.
    """
    match schema:
        case "boolean":
            return False
        case "integer":
            return 0
        case "long":
            return 0
        case "float":
            return 0.0
        case "double":
            return 0.0
        case "string":
            return ""
        case _:
            return ""


class DtdlExtendedModelData:
    """
    Class to represent a DTDL model in the model repository. It contains all the model, all
    properties (including those of the base models), telationships, ...
    """

    def __init__(self, model: object, all_models: list[object]):
        self.model = model
        self.bases: list[str] = []
        self.properties: list[DtdlProperty] = []
        self.telemetries: list[DtdlTelemetry] = []
        self.relationships: list[DtdlRelationship] = []
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
                    self.properties.append(DtdlProperty(c))
            for c in model["contents"]:
                if c["@type"] == "Telemetry" or "Telemetry" in c["@type"]:
                    self.telemetries.append(DtdlTelemetry(c))
            for c in model["contents"]:
                if c["@type"] == "Relationship" or "Relationship" in c["@type"]:
                    self.relationships.append(DtdlRelationship(c))
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
