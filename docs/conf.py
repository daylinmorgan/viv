project = "Viv"
copyright = "2023, Daylin Morgan"
author = "Daylin Morgan"

extensions = ["myst_parser", "sphinx_copybutton"]
myst_enable_extensions = ["colon_fence", "deflist"]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
html_extra_path = ["viv.py"]


html_theme = "shibuya"
# html_static_path = ["_static"]
html_logo = "../assets/logo.svg"

html_theme_options = {
    "github_url": "https://github.com/daylinmorgan/viv",
    "nav_links": [
        {"title": "Documentation", "url": "installation"},
        {"title": "CLI Reference", "url": "cli"},
    ],
}
