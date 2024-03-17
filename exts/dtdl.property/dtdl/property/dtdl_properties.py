import omni.ext
import omni.ui as ui


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
        from .example_attribute_widget import ExampleAttributeWidget

        property_window = property_window_ext.get_window()
        if property_window:
            # register ExampleAttributeWidget class with property window.
            # you can have multple of these but must have to be different scheme names
            # but always "prim" or "layer" type
            #   "prim" when a prim is selected
            #   "layer" only seen when root layer is selected in layer window
            property_window.register_widget(
                "prim", "dtdl_properties", ExampleAttributeWidget()
            )
            self._registered = True
            # ordering of property widget is controlled by omni.kit.property.bundle
