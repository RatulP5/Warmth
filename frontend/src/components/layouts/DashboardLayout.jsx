import Header from "./Header.jsx";
import Sidebar from "./Sidebar.jsx";
import "./Layout.css";
//import Sidebar from "./Sidebar.jsx";
export default function DashboardLayout({ children }) {
  //console.log("Hello");
  return (
    <div className="ops-shell">
      <Sidebar />
      <main className="ops-main">
        <Header />
        {children}
      </main>
    </div>
  );
}
