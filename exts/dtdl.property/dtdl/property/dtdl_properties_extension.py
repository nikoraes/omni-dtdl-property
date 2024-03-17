import omni.ext
import omni.ui as ui
from pxr import Sdf, Usd, UsdGeom, Gf
from omni.kit.property.usd.prim_selection_payload import PrimSelectionPayload


class DtdlPropertyExtension(omni.ext.IExt):
    def __init__(self):
        super().__init__()
        self._registered = False
        self._menu_items = []

    def on_startup(self, ext_id):
        self._register_widget()
        self._register_add_menus()

    def on_shutdown(self):
        self._unregister_add_menus()
        if self._registered:
            self._unregister_widget()

    def _register_widget(self):
        import omni.kit.window.property as property_window_ext
        from .dtdl_attribute_widget import DtdlAttributeWidget

        property_window = property_window_ext.get_window()
        if property_window:
            # register ExampleAttributeWidget class with property window.
            # you can have multple of these but must have to be different scheme names
            # but always "prim" or "layer" type
            #   "prim" when a prim is selected
            #   "layer" only seen when root layer is selected in layer window
            property_window.register_widget(
                "prim", "dtdl_properties", DtdlAttributeWidget()
            )
            self._registered = True
            # ordering of property widget is controlled by omni.kit.property.bundle

    def _unregister_widget(self):
        import omni.kit.window.property as property_window_ext

        property_window = property_window_ext.get_window()
        if property_window:
            # remove ExampleAttributeWidget class with property window
            property_window.unregister_widget("prim", "dtdl_properties")
            self._registered = False

    def _register_add_menus(self):
        from omni.kit.property.usd import PrimPathWidget

        # add menus to property window path/+add and context menus +add submenu.
        # show_fn: controls when option will be shown, IE when selected prim(s) are Xform or Mesh.
        # onclick_fn: is called when user selects menu item.
        # self._menu_items.append(
        #     PrimPathWidget.add_button_menu_entry(
        #         "Example/Hovercraft Wheels",
        #         show_fn=DtdlPropertyExtension.prim_is_example_type,
        #         onclick_fn=DtdlPropertyExtension.click_add_hovercraft_wheels,
        #     )
        # )

        # In future, maybe add menu items to change DTDl model

    def _unregister_add_menus(self):
        from omni.kit.property.usd import PrimPathWidget

        # remove menus to property window path/+add and context menus +add submenu.
        for item in self._menu_items:
            PrimPathWidget.remove_button_menu_entry(item)

        self._menu_items = None

    @staticmethod
    def prim_is_valid_type(objects: dict) -> bool:
        """
        checks if prims are required type
        """
        if "stage" not in objects or "prim_list" not in objects or not objects["stage"]:
            return False

        stage = objects["stage"]
        if not stage:
            return False

        prim_list = objects["prim_list"]
        for path in prim_list:
            if isinstance(path, Usd.Prim):
                prim = path
            else:
                prim = stage.GetPrimAtPath(path)
            if prim:
                if not (prim.IsA(UsdGeom.Xform) or prim.IsA(UsdGeom.Mesh)):
                    return False

        return len(prim_list) > 0
