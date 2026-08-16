import type { ApplePermissionPlaceholder } from "./types";

type ApplePermissionsProps = {
  permissions: ApplePermissionPlaceholder[];
};

export function ApplePermissions({ permissions }: ApplePermissionsProps) {
  return (
    <section className="settings-section" aria-labelledby="apple-permissions-heading">
      <h2 id="apple-permissions-heading">Apple permissions</h2>
      <p>Live status arrives from the Apple Bridge (M07). Placeholders until then:</p>
      <ul className="permission-list">
        {permissions.map((permission) => (
          <li key={permission.id}>
            {permission.label} — {permission.detail}
            <span className="permission-status"> [{permission.status}]</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
