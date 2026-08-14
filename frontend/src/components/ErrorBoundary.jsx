import { Component } from "react";

// 2026-08-15: render vaqtidagi kutilmagan xatolarni ushlaydi — bo'lmasa
// React butun ilovani ekrandan olib tashlaydi (oq ekran, xabar yo'q).
// Class component bo'lishi SHART — componentDidCatch hook orqali mavjud emas.
export default class ErrorBoundary extends Component {
  state = { xato: false };

  static getDerivedStateFromError() {
    return { xato: true };
  }

  componentDidCatch(error, info) {
    console.error("ErrorBoundary ushladi:", error, info);
  }

  render() {
    if (this.state.xato) {
      return (
        <div style={{ padding: 40, textAlign: "center" }}>
          <h2>Nimadir xato ketdi</h2>
          <p style={{ color: "var(--matn-sokin)" }}>
            Sahifani yangilab qayta urinib ko'ring.
          </p>
          <button className="tugma" onClick={() => window.location.reload()}>
            Sahifani yangilash
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
