# PriconneMultiAccountLauncher

ตัวช่วยสลับบัญชีและเข้าเล่นเกม Princess Connect! Re:Dive (เวอร์ชัน PC บน DMM) ได้อย่างรวดเร็ว ปลอดภัย และไร้รอยต่อ 100%

[![GitHub Downloads](https://img.shields.io/github/downloads/HetCreep/PriconneMultiAccountLauncher/total)](https://github.com/HetCreep/PriconneMultiAccountLauncher/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

[ภาษาไทย](/README.md) / [English](/README-en.md)

---

## 🌟 คุณสมบัติเด่น (Features)

*   **สลับบัญชีไร้รอยต่อและไม่โหลดไฟล์เกมซ้ำ (Flawless Swapping):** ระบบจะสำรอง/กู้คืน **เฉพาะ** ค่าใน Windows Registry ของ Cygames (`HKCU\Software\Cygames\PrincessConnectReDive`) แยกตามรายบัญชีโดยอัตโนมัติ ส่วนไฟล์ข้อมูลเกม (`manifest.db` และแคชใน LocalLow) เป็นข้อมูล asset ที่ใช้ร่วมกันทุกบัญชี จึงไม่ถูกแตะต้อง **ช่วยให้สลับไอดีได้โดยไม่บังคับดาวน์โหลดข้อมูลเกมใหม่**
*   **กู้คืนสถานะอัตโนมัติ (Baseline & Restore-on-Exit):** ก่อนใช้งานครั้งแรกจะบันทึกสถานะบัญชีหลักของท่านไว้เป็น baseline และกู้คืนกลับมาทุกครั้งหลังปิดเกม หากโปรแกรมถูกบังคับปิดกลางคัน ระบบจะกู้คืน baseline ให้ในการเปิดครั้งถัดไป
*   **ระบบต่อต้านการตรวจจับประสิทธิภาพสูง (Anti-Detection):** จำลองรหัสฮาร์ดแวร์คงที่ส่วนบุคคลแบบล็อกรายบัญชี (`mac_address`, `hdd_serial`, `motherboard`) ไม่มีการสุ่มเปลี่ยนค่าทุกครั้งที่เปิดรัน ทำให้เซิร์ฟเวอร์ DMM ตรวจจับเป็นคอมพิวเตอร์เครื่องเดิมตลอดเวลา
*   **เข้าเกมได้ทันที (Direct Launch):** หลังสลับค่า Registry แล้วจะสั่งเปิดไฟล์เกมโดยตรง ไม่ต้องผ่านหน้าต่างหลักของ DMM Client ช่วยประหยัดเวลาและทรัพยากรเครื่อง
*   **อัปเดตอัตโนมัติ (Auto-Updater):** ตรวจสอบเวอร์ชันล่าสุดจาก GitHub Releases และแจ้งเตือนเท่านั้น (เปิดหน้าดาวน์โหลดในเบราว์เซอร์ ไม่ติดตั้งให้อัตโนมัติ) สามารถปิดได้ที่ Settings → Advanced

---

## 💾 การติดตั้ง (Installation)

1.  ดาวน์โหลดตัวติดตั้ง (installer) หรือไฟล์ zip แบบพกพา (portable) เวอร์ชันล่าสุดได้ที่หน้า [Releases](https://github.com/HetCreep/PriconneMultiAccountLauncher/releases) เท่านั้น (ไฟล์ที่เผยแพร่ถูกสร้างผ่าน GitHub Actions ไม่ใช่บิลด์จากเครื่องส่วนตัว)
2.  แต่ละรีลีสจะแนบไฟล์ `SHA256SUMS.txt` และ SBOM ไว้ให้ตรวจสอบความถูกต้องของไฟล์ก่อนรัน
3.  ดับเบิลคลิกตัวติดตั้งเพื่อดำเนินการตามวิซาร์ดจนเสร็จสิ้น

---

## 🛠️ วิธีใช้งาน (Usage)

1.  เปิดตัวโปรแกรมหลักผ่านไอคอนบนหน้าจอเดสก์ท็อป หรือจากโฟลเดอร์ที่ติดตั้งไว้
2.  ไปที่หน้าต่าง **Account** เพื่อนำเข้าไอดี DMM มีให้เลือก 2 วิธี:
    *   **Import from DMM** — อ่านโทเค็นจาก DMM Game Player ที่ล็อกอินอยู่แล้วในเครื่อง
    *   **Import from Browser** — ล็อกอิน DMM ผ่านเบราว์เซอร์เริ่มต้นของระบบ (ตรวจหาเบราว์เซอร์ให้อัตโนมัติ ไม่ต้องเลือกเอง)
3.  สร้างทางลัด (Shortcut) สำหรับบัญชีแต่ละบัญชีที่ต้องการ
4.  ดับเบิลคลิกที่ทางลัดเพื่อรันเล่นเกมและสลับไปมาระหว่างบัญชีได้ทันที!

> **หมายเหตุเรื่องภูมิภาค:** DMM เวอร์ชันเกมถูกล็อกเฉพาะประเทศญี่ปุ่น (JP) หากท่านอยู่นอกญี่ปุ่น ต้องตั้งค่าพร็อกซีของญี่ปุ่นที่ **Settings → Advanced** ก่อนล็อกอินและเปิดเกม

---

## 🤝 การสนับสนุนและการรายงานปัญหา (Support & Contribution)

*   **รายงานปัญหา (Bug Report):** เปิดหัวข้อแจ้งปัญหาได้ที่ช่องทาง [Issues](https://github.com/HetCreep/PriconneMultiAccountLauncher/issues)
*   **การมีส่วนร่วม:** สามารถร่วมพัฒนาโมดูลและสนับสนุนโปรเจกต์ได้ที่ลิงก์หลัก [HetCreep/PriconneMultiAccountLauncher](https://github.com/HetCreep/PriconneMultiAccountLauncher)

---

## ⚠️ คำชี้แจง (Disclaimer)

โปรแกรมนี้เป็นเครื่องมือที่พัฒนาโดยอิสระจากบุคคลที่สาม (Unofficial third-party launcher)
**ไม่ได้รับการสนับสนุน ไม่ได้สังกัด และไม่มีความเกี่ยวข้องใดๆ กับ DMM.com LLC หรือ Cygames Inc.**

- "Princess Connect! Re:Dive" และ "プリンセスコネクト！Re:Dive" เป็นเครื่องหมายการค้าของ Cygames Inc.
- "DMM", "DMM GAMES", "DMM Game Player" เป็นเครื่องหมายการค้าของ DMM.com LLC
- การใช้โปรแกรมนี้อาจขัดต่อข้อกำหนดการให้บริการ (Terms of Service) ของ DMM หรือ Cygames และอาจส่งผลให้บัญชีของท่านถูกระงับ
- ผู้พัฒนาเผยแพร่ซอฟต์แวร์นี้ในสภาพ "AS-IS" โดยไม่มีการรับประกันใดๆ และไม่รับผิดชอบต่อการกระทำใดๆ ที่ DMM หรือ Cygames อาจดำเนินการต่อบัญชีของท่าน
- ใช้งานด้วยความเสี่ยงของท่านเอง (USE AT YOUR OWN RISK)

โปรดอ่าน [PRIVACY.md](PRIVACY.md) และ [SECURITY.md](SECURITY.md) ก่อนใช้งาน

---

## 📄 ใบอนุญาต (License)

ซอฟต์แวร์นี้อยู่ภายใต้ใบอนุญาต **MIT License**
