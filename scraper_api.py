from fastapi import FastAPI, HTTPException
from playwright.async_api import async_playwright
from fastapi import FastAPI, HTTPException
from playwright.async_api import async_playwright
import os # <--- YEH NAYA HAI
import json
import uvicorn
import json
import uvicorn

app = FastAPI(title="MDSK Auto-Bypass RTO API")

@app.get("/")
def read_root():
    return {"message": "API is live! Use /api/v1/rto/{vehicle_no}"}

@app.get("/api/v1/rto/{vehicle_no}")
async def get_rto(vehicle_no: str):
    async with async_playwright() as p:
        # Browser start karna
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            # 1. Cars24 par jana taaki Cloudflare cookies mil jayein
            await page.goto("https://www.cars24.com/car-service-history/", wait_until="domcontentloaded")
            
            # 2. Browser ke andar dono API (Token + Data) execute karna
            script = """
            async (v_no) => {
                const dummyPhone = "9" + Math.floor(10000000 + Math.random() * 90000000);
                const dummyId = crypto.randomUUID();
                
                // Step A: Token nikalna
                const res1 = await fetch('https://seller-lead.cars24.team/prospect/lead', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        phone: dummyPhone,
                        vehicle_reg_no: v_no,
                        user_id: dummyId,
                        whatsapp_consent: true,
                        type: 'service_history',
                        device_category: 'Desktop'
                    })
                });
                const data1 = await res1.json();
                if (!data1.detail || !data1.detail.token) return {error: "Token fetch failed", full_resp: data1};
                
                const token = data1.detail.token;
                
                // Step B: RTO details nikalna
                const res2 = await fetch('https://seller-lead.cars24.team/prospect/lead/v2/service-history/' + token + '?checkGsInventory=true', {
                    method: 'GET'
                });
                return await res2.json();
            }
            """
            
            raw_data = await page.evaluate(script, vehicle_no)
            await browser.close()
            
            if "error" in raw_data:
                raise HTTPException(status_code=500, detail=raw_data)
                
            if "vehicleRegistrationDetails" not in raw_data or not raw_data['vehicleRegistrationDetails']:
                 raise HTTPException(status_code=404, detail="Is gaadi ka data nahi mila.")
                 
            v_info = raw_data['vehicleRegistrationDetails']
            full_details_str = v_info.get('full_details', '{}')
            
            try:
                full_details = json.loads(full_details_str)
            except:
                full_details = {}
            
            return {
                "status": "success",
                "data": {
                    "rc_number": v_info.get("registrationNumber", vehicle_no),
                    "state": full_details.get("registeredPlace", "Unknown"),
                    "owner_name": v_info.get("rc_owner_name", ""),
                    "owner_serial": v_info.get("rc_owner_sr", ""),
                    "make_model": f"{v_info.get('brand', {}).get('make_display', '')} {v_info.get('model', {}).get('model_display', '')}".strip(),
                    "manufacturing_year": v_info.get("year", {}).get("year", ""),
                    "fuel_type": v_info.get("fuelType", ""),
                    "color": v_info.get("color", ""),
                    "chassis_no": full_details.get("chassisNo", ""),
                    "engine_no": full_details.get("engineNo", ""),
                    "insurance_upto": v_info.get("insuranceUpTo", ""),
                    "fitness_upto": v_info.get("fitnessUpTo", ""),
                    "financier": full_details.get("financier", "On Cash"),
                    "rc_status": full_details.get("rcStatus", "Unknown")
                }
            }
            
        except Exception as e:
            await browser.close()
            raise HTTPException(status_code=500, detail=f"System Error: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
