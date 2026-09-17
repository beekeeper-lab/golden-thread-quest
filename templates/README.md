# Template Design Contracts

These `.j2` files are illustrative contracts for the implementation agent. They demonstrate the expected separation between normalized view models and presentation.

They are not a finished theme and are not wired to a Python builder in this design package.

Rules:

- Templates receive route-ready, display-ready view models.
- Autoescaping remains enabled.
- Quest-specific text and business rules do not appear in templates.
- Markdown is sanitized before being marked as rendered content.
- Shared components own consistent state and authority labels.
- URLs come from route helpers represented in the view model.
