export function SettingsPage() {
  return (
    <section className="page">
      <h1>Settings</h1>
      <p>Apple data permissions will appear here (Calendar, Reminders, Contacts, Notes).</p>
      <ul className="permission-list">
        <li>Calendar — read access (pending Apple Bridge)</li>
        <li>Reminders — read access (pending Apple Bridge)</li>
        <li>Contacts — read access (pending Apple Bridge)</li>
        <li>Notes — automation, opt-in (pending Apple Bridge)</li>
      </ul>
    </section>
  );
}
