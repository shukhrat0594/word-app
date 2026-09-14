import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import "./index.css";
import App from "./App.jsx";
import { FilialProvider } from "./filialContext.jsx";
import { I18nProvider } from "./i18n.jsx";

// Saqlangan tema (yorug'/qorong'u) — kalit LMS bilan bir xil, ya'ni
// admin bir marta tanlagan tema ikkala ilovada ham ishlaydi.
const tema = localStorage.getItem("tema");
if (tema) document.documentElement.dataset.theme = tema;

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <I18nProvider>
      <FilialProvider>
        <App />
      </FilialProvider>
    </I18nProvider>
  </StrictMode>,
);
