import os
import time
import subprocess
import requests
from fpdf import FPDF

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

def wait_for_server(url, timeout=10):
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(url)
            if r.status_code == 200:
                return True
        except:
            pass
        time.sleep(0.5)
    return False

def generate_screenshots():
    if not PLAYWRIGHT_AVAILABLE:
        print("\n[NOTE] Playwright is not installed on this environment.")
        print("Skipping live screenshot generation. Will use existing screenshots if available.\n")
        return

    print("Starting backend...")
    backend_env = os.environ.copy()
    backend_env["DB_PATH"] = "register.db"
    backend_proc = subprocess.Popen(["python", "app.py"], cwd="backend", env=backend_env)
    
    print("Starting frontend...")
    frontend_proc = subprocess.Popen(["python", "-m", "http.server", "8080"], cwd="frontend")
    
    try:
        # Seed the data first
        print("Seeding database...")
        subprocess.run(["python", "seed_data.py"], cwd="backend", env=backend_env)
        
        print("Waiting for servers...")
        if not wait_for_server("http://localhost:5000/api/health"):
            print("Backend failed to start")
            return
        if not wait_for_server("http://localhost:8080/"):
            print("Frontend failed to start")
            return
            
        print("Taking screenshots...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1200, "height": 800})
            
            # Go to Capture
            page.goto("http://localhost:8080/")
            time.sleep(1)
            page.screenshot(path="capture.png")
            
            # Go to Register
            page.click("button[data-tab='register']")
            time.sleep(1)
            page.screenshot(path="register.png")
            
            # Go to Usage
            page.click("button[data-tab='usage']")
            time.sleep(1)
            page.screenshot(path="usage.png")
            
            browser.close()
            
    finally:
        print("Terminating servers...")
        backend_proc.terminate()
        frontend_proc.terminate()

class PDF(FPDF):
    def header(self):
        self.set_font("helvetica", "B", 15)
        
    def footer(self):
        self.set_y(-15)
        self.set_font("helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", 0, 0, "C")

def create_presentation():
    pdf = PDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Slide 1: Title
    pdf.add_page()
    pdf.set_font("helvetica", "B", 24)
    pdf.cell(0, 80, "")
    pdf.ln()
    pdf.cell(0, 10, "Institutional Vehicle Booking and Usage Register", 0, 0, "C")
    pdf.ln()
    pdf.set_font("helvetica", "", 16)
    pdf.cell(0, 10, "A practical solution for transport management", 0, 0, "C")
    pdf.ln()
    pdf.cell(0, 10, "By Bharath E - PDKVCET - AIDS", 0, 0, "C")
    pdf.ln()
    
    # Slide 2: The Problem & Who is Affected
    pdf.add_page()
    pdf.set_font("helvetica", "B", 20)
    pdf.cell(0, 20, "1. The Problem & Who is Affected")
    pdf.ln()
    pdf.set_font("helvetica", "", 16)
    pdf.multi_cell(0, 10, "Problem:\n- Vehicles are booked via phone calls and a paper diary.\n- Double bookings are common and discovered too late.\n- No record of actual usage, making it impossible to attribute costs to departments.\n\nWho is affected:\n- The Transport Clerk (stressful double-bookings).\n- Departments (delayed or missing vehicles).\n- The Transport Officer (no data for cost tracking).")
    
    # Slide 3: Our Solution
    pdf.add_page()
    pdf.set_font("helvetica", "B", 20)
    pdf.cell(0, 20, "2. Our Solution")
    pdf.ln()
    pdf.set_font("helvetica", "", 16)
    pdf.multi_cell(0, 10, "A digital register that securely records bookings, automatically blocks overlapping requests, and instantly calculates distance usage per department.")
    
    # Slide 4: Capture Screen
    pdf.add_page()
    pdf.set_font("helvetica", "B", 20)
    pdf.cell(0, 10, "3. Capture Booking")
    pdf.ln()
    if os.path.exists("capture.png"):
        pdf.image("capture.png", x=10, y=30, w=270)
    else:
        pdf.set_draw_color(180, 180, 180)
        pdf.rect(10, 30, 270, 150, "D")
        pdf.set_xy(10, 100)
        pdf.set_font("helvetica", "I", 14)
        pdf.cell(270, 10, "[Screenshot Placeholder: Capture Booking Screen]", 0, 0, "C")
        
    # Slide 5: Register View
    pdf.add_page()
    pdf.set_font("helvetica", "B", 20)
    pdf.cell(0, 10, "4. Register View")
    pdf.ln()
    if os.path.exists("register.png"):
        pdf.image("register.png", x=10, y=30, w=270)
    else:
        pdf.set_draw_color(180, 180, 180)
        pdf.rect(10, 30, 270, 150, "D")
        pdf.set_xy(10, 100)
        pdf.set_font("helvetica", "I", 14)
        pdf.cell(270, 10, "[Screenshot Placeholder: Register View Screen]", 0, 0, "C")
        
    # Slide 6: Usage Dashboard
    pdf.add_page()
    pdf.set_font("helvetica", "B", 20)
    pdf.cell(0, 10, "5. Usage Dashboard & Derived Figures")
    pdf.ln()
    pdf.set_font("helvetica", "", 12)
    pdf.multi_cell(0, 6, "Derived figures (Total KM and Trip Count) are calculated on the server. Bookings without KM yet are excluded from total distance but included in trip count.")
    if os.path.exists("usage.png"):
        pdf.image("usage.png", x=10, y=40, w=200)
    else:
        pdf.set_draw_color(180, 180, 180)
        pdf.rect(10, 40, 270, 140, "D")
        pdf.set_xy(10, 100)
        pdf.set_font("helvetica", "I", 14)
        pdf.cell(270, 10, "[Screenshot Placeholder: Usage Dashboard Screen]", 0, 0, "C")
        
    # Slide 7: What Works & Unfinished Features
    pdf.add_page()
    pdf.set_font("helvetica", "B", 20)
    pdf.cell(0, 20, "6. What Works & Unfinished Features")
    pdf.ln()
    pdf.set_font("helvetica", "", 16)
    pdf.multi_cell(0, 10, "What Works:\n- Full end-to-end booking capture and validation.\n- Server-side double booking prevention.\n- Real-time usage aggregation by department.\n- Offline mode (queues bookings and syncs when reconnected).\n\nUnfinished:\n- No authentication/login system.\n- No edit or cancel UI directly from the frontend.")
    
    # Slide 8: Next Improvements
    pdf.add_page()
    pdf.set_font("helvetica", "B", 20)
    pdf.cell(0, 20, "7. Next Improvement")
    pdf.ln()
    pdf.set_font("helvetica", "", 16)
    pdf.multi_cell(0, 10, "Next Step: Add a vehicles table (make, capacity, fuel type) to calculate the actual financial cost per department, not just the distance traveled.")
    
    pdf.output("presentation.pdf")
    print("presentation.pdf created successfully.")

if __name__ == "__main__":
    generate_screenshots()
    create_presentation()
