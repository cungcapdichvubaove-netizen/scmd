# FULL_INTEGRATED_MANIFEST.md — SCMD Pro Full Integrated Source V15

Base: `scmd_pro_full_integrated_operations_ux_v14.zip`.
Overlay: Compact Operations Admin System V15 patch.

This ZIP is a full integrated source package for development/integration, not a built production artifact.

## Integrated fixes retained

- StaffVisibilityPolicy / object-scope preservation.
- Global search single-widget implementation with admin queryset scope from V12.
- Compact admin table-first V10 layout.
- Bulk status confirmation/audit governance from V8/V9.
- Brand token/dark-mode dashboard hardening from V13/V14.
- Artifact hygiene cleanup from previous versions.

## V15 focus

- SCMD Pro mobile base shell replaces the boilerplate Django Tailwind starter shell.
- Inventory dashboard joins the shared dashboard token/design system.
- Shared skeleton/loading/empty/error state classes added.
- Breakpoint contract added to UI governance spec.

## Runtime status

Static/source verification: PASS.
Docker/runtime/browser verification: NOT VERIFIED in sandbox.
