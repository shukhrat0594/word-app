import { createContext, useContext, useState } from "react";

const TestRejimiContext = createContext(null);

/** Butun ilova bo'ylab "test hozir faol (yechilmoqda)mi" holatini saqlaydi
 * (2026-07-30, foydalanuvchi talabi: "test tugamaguncha boshqa bo'limga
 * o'tish mumkin bo'lmasin"). `Layout.jsx` shu holatga qarab navigatsiyani
 * bloklaydi, `ImtihonOtish.jsx`/`ImtihonYozGap.jsx`/`ImtihonMock.jsx` esa
 * test boshlanganda/tugaganda shu holatni yangilaydi. */
export function TestRejimiProvider({ children }) {
  const [testFaol, setTestFaol] = useState(false);
  return (
    <TestRejimiContext.Provider value={{ testFaol, setTestFaol }}>
      {children}
    </TestRejimiContext.Provider>
  );
}

export const useTestRejimi = () => useContext(TestRejimiContext);
