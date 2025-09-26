"""
Available themes list
Used by context provider and forms
"""

CODEMIRROR_THEMES = [ # 66
    "default", "3024-day","3024-night","abbott","abcdef","ambiance-mobile","ambiance",
    "ayu-dark","ayu-mirage","base16-dark","base16-light","bespin","blackboard",
    "cobalt","colorforth","darcula","dracula","duotone-dark","duotone-light",
    "eclipse","elegant","erlang-dark","gruvbox-dark","hopscotch","icecoder",
    "idea","isotope","juejin","lesser-dark","liquibyte","lucario",
    "material-darker","material-ocean","material-palenight","material","mbo",
    "mdn-like","midnight","monokai","moxer","neat","neo","night","nord",
    "oceanic-next","panda-syntax","paraiso-dark","paraiso-light",
    "pastel-on-dark","railscasts","rubyblue","seti","shadowfox","solarized",
    "ssms","the-matrix","tomorrow-night-bright","tomorrow-night-eighties",
    "ttcn","twilight","vibrant-ink","xq-dark","xq-light","yeti","yonce",
    "zenburn"
]

BOOTSWATCH_THEMES = [
    "default",  "cerulean", "cosmo", "cyborg", "darkly", "flatly", "journal",
    "litera", "lumen", "materia", "minty", "pulse",
    "sandstone", "simplex", "solar", "spacelab", "superhero",
    "united", "yeti", "brite"
] 
# BANNED - "quartz", "lux", "superhero", "slate", "sketchy", "vapor", "brite",
# "zephyr", "morph"

# TODO: Make presets, add presets menu to user settings.
PRESETS = {
    # "Preset Name" : ("Bootswatch", "codemirror"),
    "Material Dark" : ("Darkly", "material-darker"),
}