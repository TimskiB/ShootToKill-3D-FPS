from kivy.lang.builder import Builder
from kivy.uix.screenmanager import Screen
from kivymd.app import MDApp
from kivymd.uix.list import MDList, OneLineListItem

from kivymd_extensions.akivymd.uix.behaviors.addwidget import (
    AKAddWidgetAnimationBehavior,
)

Builder.load_string(
    """
<AddWidgetBehavior>:
    BoxLayout:
        orientation: "vertical"
        MDToolbar:
            id: _toolbar
            title: 'Create a New Lobby:'
        ScrollView:
            AnimatedBox:
                id: list
                transition: "fade_size"
"""
)


class AnimatedBox(MDList, AKAddWidgetAnimationBehavior):
    pass


class MainApp(MDApp):
    def build(self):
        return AddWidgetBehavior()


class AddWidgetBehavior(Screen):
    def on_enter(self):
        self.update()

    def update(self, *args):
        items = []
        for x in range(20):
            items.append(
                OneLineListItem(text=f"Item {x}", on_release=self.update)
            )
        self.ids.list.items = items

    def on_leave(self):
        self.ids.list.clear_widgets()


MainApp().run()
