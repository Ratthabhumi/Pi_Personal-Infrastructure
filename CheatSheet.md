# 🏆 MASTER CLASS: HOMELAB CLOUD & SRE PLATFORM CHEATSHEET
> **คัมภีร์สรุประบบ Enterprise Zero-Trust HomeLab & Observability (ฉบับจบในแผ่นเดียว)**
> *สร้างและพัฒนาโดย: Ratthabhumi & Antigravity (Advanced Agentic AI)*

---

## 🏛️ 1. สัตยาธิษฐานแห่งสถาปัตยกรรม (Core Architectural Concept)
เราได้ทำการแปลงร่างเซิร์ฟเวอร์โน้ตบุ๊ก **Acer Aspire V13 (`mew@homelab`)** ให้กลายเป็นศูนย์บัญชาการ **Cloud-Native & Platform Engineering** ยุคใหม่ โดยออกแบบให้อยู่ภายใต้ปรัชญา:
1. **Lightweight & High Performance:** เลือกใช้ **Docker Containers** (แทน Virtual Machines) เพื่อประหยัด CPU/RAM ไว้รัน AI และ Services หนักๆ ได้สูงสุด
2. **GitOps Single-Source-of-Truth:** โค้ดทุกบรรทัดและคอนฟิกเซิร์ฟเวอร์ถูกเขียนและพัฒนาบนเครื่องทำงาน PC (VS Code) และซิงค์ขึ้น **GitHub** ก่อนจะถูกสั่งบูตที่เซิร์ฟเวอร์ผ่านระบบ GitOps 
3. **Zero-Trust Mesh Networking:** ใช้ **Tailscale Overlay Network** + **Traefik Edge Gateway** ปิดกั้นพอร์ตอันตราย และทะลุผ่าน Nat/Firewall ด้วยความปลอดภัยระดับองค์กร

---

## ⚙️ 2. คัมภีร์คำสั่งสั่งการหลัก (GitOps & Makefile Engine)
ในการอัปเดตหรือติดตั้งระบบใหม่ ให้ยึดกระบวนการ **"Golden GitOps Loop"** เสมอ:

### 🌟 2.1 คำสั่งบนฝั่งเครื่องคนทำงาน (Terminal ใน VS Code PC)
เมื่อคุณเขียนโค้ดหรือแก้ไขไฟล์คอนฟิกเสร็จแล้ว:
```powershell
# 1. เช็กสถานะไฟล์ที่ถูกปรับปรุง
git status

# 2. เตรียมแพ็คไฟล์ทั้งหมดเข้าคลัง
git add .

# 3. ประทับตราบันทึกข้อความอัปเดต (Commit Message)
git commit -m "⚡ รายละเอียดสิ่งที่คุณแก้ไขหรือเพิ่มเติม"

# 4. ดันโค้ดพุ่งทะยานขึ้นคลาวด์ GitHub
git push -u origin main
```

---

### 🌟 2.2 คำสั่งบนฝั่งเซิร์ฟเวอร์ (Terminal ในจอ SSH `mew@homelab`)
เมื่อล็อกインเข้าเซิร์ฟเวอร์แล้ว ให้เดินทางเข้าโฟลเดอร์หลักแล้วสั่งการด้วย **Makefile Engine**:

```bash
# 1. เดินทางเข้าโฟลเดอร์คลังศูนย์กลางโลก Homelab
cd ~/Pi_Personal-Infrastructure    # (หรือใช้คำสั่งลัด: cdlab)

# 2. ดึงอัปเดตโค้ดล่าสุดจากคลาวด์ GitHub มาสถิตที่โน้ตบุ๊ก
git pull origin main
```

| คำสั่ง Makefile สั่งการ | หน้าที่และความหมาย (What it does) |
| :--- | :--- |
| `make apply-local` | 🛡️ **Self-Bootstrapping:** ปลุกระบบ Ansible ตรวจเช็กและปรับจูนความปลอดภัย OS, โหลด Docker Engine และเปิด UFW Firewall อัตโนมัติ |
| `make core-up` | 🚀 **Start Core Stack:** เปิดใช้งานประตูเฝ้ายาม **Traefik (Reverse Proxy)** และศูนย์คุมระบบ **Portainer CE (Web UI)** |
| `make obs-up` | 📊 **Start Observability Stack:** เปิดตู้เครื่องมือแพทย์ **VictoriaMetrics**, **Node Exporter**, **cAdvisor** และห้องบัญชาการ **Grafana** |
| `make autodox` | 📝 **Autonomous Documenter:** ปลุกหุ่นยนต์ Python สแกนสถานะทุก Container และอัปเดตไฟล์สถิติ [live_inventory.md](file:///c:/Users/MewMew/Desktop/Co-op/Pi_Personal-Infrastructure/docs/architecture/live_inventory.md) อัตโนมัติ |
| `make backup` | 🛡️ **Snapshot & Backup Engine:** แพ็กข้อมูล Volume สำคัญ (Grafana/Portainer) เป็น `.tar.gz` พร้อมลบไฟล์สถิติเก่าเกิน 7 วันออกอัตโนมัติ |
| `make status` | 🔍 **Health Inspector:** ตรวจดูชื่อ Container ทั้งหมดที่กำลังทำงาน พร้อมมาตรวัดกิน RAM/CPU แบบเรียลไทม์ |
| `make core-down` | 🛑 **Shutdown Core:** ปิดพักระบบ Traefik & Portainer อย่างนิ่มนวล (ข้อมูลไม่สูญหาย) |
| `make obs-down` | 🛑 **Shutdown Observability:** ปิดพักระบบ Grafana & VictoriaMetrics อย่างนิ่มนวล (ข้อมูลไม่สูญหาย) |

---

## 🔥 3. คำสั่งลัดประจำมือวิศวกร (Bash Super Aliases)
เพื่อลดเวลาพิมพ์ยาวๆ ระบบได้รับการเสกคาถาคำสั่งลัดฝังไว้ใน `.bashrc` ของเครื่อง Ubuntu แล้ว:
* **`cdlab`**  👉 กระโดดวาร์ปเข้าโฟลเดอร์ `~/Pi_Personal-Infrastructure` ทันทีจากทุกที่ในระบบ!
* **`dps`**    👉 แสดงรายชื่อ Docker Containers ที่รันอยู่ด้วยกราฟิกและสีที่สะอาดตา ดูง่ายกว่า `docker ps` ทั่วไป 10 เท่า
* **`dlog <ชื่อตู้>`** 👉 ดูคลื่นบันทึกการทำงาน (Logs) แบบเรียลไทม์ของตู้ที่ต้องการ เช่น `dlog victoriametrics` หรือ `dlog traefik`
* **`dstop <ชื่อตู้>`** 👉 ปิดและถอดถอน Container ที่เกิดอาการค้างออกจากระบบอย่างฉับไว

---

## 🌐 4. ตารางพิกัดเข้าใช้งานระบบผ่านหน้าเว็บ (Web UI Matrix)
คุณสามารถเปิดโปรแกรมเว็บเบราว์เซอร์บนเครื่อง Dell Windows Workstation หรืออุปกรณ์ในเครือข่าย Tailscale เพื่อเข้าใช้งานระบบได้ทันที:

| บริการ (Service) | พอร์ต / ลิงก์เข้าเว็บ | หน้าที่รับผิดชอบ | ข้อมูลล็อกอินเริ่มต้น (Credentials) |
| :--- | :--- | :--- | :--- |
| **Portainer CE** | `https://homelab:9443`<br>*(หรือ `https://100.116.167.3:9443`)* | แผงควบคุมกดคลอด ตรวจสอบ และสั่งการ Docker Container ผ่านปุ่มบนเว็บ โดยไม่ต้องพิมพ์คำสั่ง | *ตั้งค่ารหัสผ่านใหม่เองในการเข้าใช้งานครั้งแรก* |
| **Grafana** | `http://homelab:3000`<br>*(หรือ `http://100.116.167.3:3000`)* | ห้องบัญชาการจอภาพ Mission Control สไตล์ NASA/Cyberpunk แปลงตัวเลขเป็นกราฟิกสวยหรู 24 ชั่วโมง | **User:** `admin`<br>**Pass:** `admin123` *(ระบบจะให้ตั้งใหม่)* |
| **VictoriaMetrics** | `http://100.116.167.3:8428` | เครื่องยนต์ Time-Series Database ที่เก็บข้อมูลชีพจร (เร็วกว่า และประหยัดแรมกว่า Prometheus 5 เท่า!) | - |
| **Traefik** | `http://100.116.167.3:80`<br>`https://100.116.167.3:443` | ตำรวจจราจรผู้แจกแจง Domain name และ SSL Certificate ให้ทุกแอปในบ้าน (Edge Ingress Gateway) | - |

---

## 🔮 5. กลเม็ดรหัสวิเศษเสกกัปตัน SRE (Grafana Magic Dashboards)
ในหน้าจอเว็บ **Grafana (`http://homelab:3000`)** คุณไม่ต้องปวดหัวนั่งสร้างกราฟเอง ให้ทำตามขั้นตอนนี้เพื่อโหลดกราฟระดับโลก:
1. คลิกเมนูซ้ายมือ **`Dashboards`** -> คลิกปุ่ม **`New`** มุมขวาบน -> เลือก **`Import`**
2. กรอกตัวเลข **Magic ID** ลงในช่อง *Import via grafana.com* -> กดปุ่ม **`Load`**
3. ด้านล่างสุดเลือกพอยต์ไปที่ **`VictoriaMetrics`** (ซึ่งถูกเชื่อมต่อสายไว้อัตโนมัติแล้ว) -> กด **`Import`**

### 🎯 รายชื่อ Magic ID สุดแกร่งที่ควรติดห้องไว้:
* 🌟 **ID: `1860` (Node Exporter Full):** ปรอทวัดไข้ฮาร์ดแวร์เซิร์ฟเวอร์ตัวจริง เสียงจริง! แสดงความร้อน CPU, เปอร์เซ็นต์ใช้ RAM, ความเร็วอ่านเขียนฮาร์ดแวร์ และสถิติเน็ตเวิร์ก
* 🌟 **ID: `14282` (Docker Containers Vitals):** เจาะลึกชีพจรของทุก Docker Container ที่รันอยู่ในบ้านว่าตู้ไหน (เช่น AI / Traefik / Portainer) แอบกินสเปคเครื่องอยู่เท่าไหร่!

> [!TIP]
> **เคล็ดลับกับดักเวลา (Time Range Trap):** หากเปิดกราฟเข้ามาแล้วพบว่าตัวเลขขึ้น `N/A` หรือ `No data` **ไม่ต้องตกใจ!** นั่นเพราะระบบเพิ่งรันได้ไม่กี่นาที แต่ Grafana ตั้งค่าเบื้องต้นให้แสดงผลย้อนหลัง 24 ชั่วโมง (`Last 24 hours`)  
> **วิธีแก้:** ให้คลิกเปลี่ยนสเกลเวลาที่มุมขวาบนสุดจาก `Last 24 hours` เปลี่ยนเป็น 👉 **`Last 5 minutes`** หรือ **`Last 15 minutes`** กราฟทุกช่องจะพุ่งขึ้นมาทันที!

---

## 🛠️ 6. คู่มือแก้ไขปัญหาฉับพลันสไตล์วิศวกร SRE (Troubleshooting & Diagnostics)

### 🚨 ปัญหา 1: หน้าเว็บ Grafana ขึ้นแถบสีแดงด่าว่า *"An error occurred within the plugin"* หรือ *"dial tcp: lookup victoriametrics on 127.0.0.11"*
* **สาเหตุที่แท้จริง (Root Cause):** ตู้เซิร์ฟเวอร์เก็บชีพจรหลังบ้าน (`victoriametrics`) เปิดไม่ขึ้นหรือสลบไป ทำให้ระบบเบอร์โทรภายในของ Docker (Internal DNS) ปฏิเสธการเชื่อมต่อจาก Grafana
* **วิธีสกัดจับและซ่อมบำรุง:**
  1. ในหน้าจอ SSH พิมพ์ `dps` เพื่อดูว่ามีรายชื่อตู้ `victoriametrics` หรือไม่
  2. พิมพ์ `dlog victoriametrics` เพื่ออ่านบรรทัดสุดท้าย (Fatal Logs) จะรู้ทันทีว่าพังเพราะคอนฟิกพิมพ์ผิด หรือติดปัญหาอะไร
  3. เมื่อแก้โค้ดในคอม PC แล้ว สั่งดึงอัปเดตและบูตใหม่ด้วย:
     ```bash
     cd ~/Pi_Personal-Infrastructure && git pull && make obs-up
     ```

### 🚨 ปัญหา 2: ในหน้า SSH พิมพ์คำว่า make แล้วระบบด่าว่า *Command 'make' not found*
* **สาเหตุและวิธีแก้:** เกิดขึ้นในเครื่อง Ubuntu ที่เพิ่งลงระบบใหม่ สามารถสั่งติดตั้งชุดเครื่องมือ Compile ได้ด้วยคำสั่งเดียว:
  ```bash
  sudo apt update && sudo apt install -y make
  ```

### 🚨 ปัญหา 3: อยากเข้าดูว่า Container ในบ้านคุยกันรู้เรื่องไหม (Network Ping Diagnostic)
* สามารถสั่งใช้สคริปต์ Docker เช็คสถานะหรือ Ping หากันในเครือข่ายวงแลนเสงี่ยม `homelab_mesh` ได้ตลอดเวลา:
  ```bash
  # ดูรายชื่อวงแลน Docker ในบ้านทั้งหมด
  docker network ls
  ```

---
*🚀 **Keep Building, Keep Escalating, and Never Stop Learning!** 🚀*
