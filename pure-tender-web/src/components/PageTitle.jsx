export default function PageTitle({ title, subtitle, action }) {
  return (
    <div className="studio-page-heading">
      <div>
        <p className="tb-eyebrow">YOUR WORKSPACE</p>
        <h1>{title}</h1>
        {subtitle && <p className="studio-page-subtitle">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}
