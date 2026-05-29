import re
import os
import asyncio
from telethon import TelegramClient, functions, types
from telethon.errors import FloodWaitError, RPCError

API_ID = int(os.environ.get("TG_API_ID", 0))
API_HASH = os.environ.get("TG_API_HASH", "")
SESSION_NAME = os.environ.get("TG_SESSION", "osint_session")

def clean_phone(phone: str) -> str:
    cleaned = re.sub(r'[^\d+]', '', phone)
    if not cleaned.startswith('+'):
        if len(cleaned) == 10:
            cleaned = '+91' + cleaned
        elif len(cleaned) == 11 and cleaned.startswith('0'):
            cleaned = '+91' + cleaned[1:]
        else:
            cleaned = '+' + cleaned
    return cleaned

def _get_indian_info(phone: str) -> dict:
    """Get carrier and location estimates for Indian numbers."""
    info = {"carrier": "Unknown", "location": "India"}
    prefix = phone[3:7] if len(phone) >= 7 else ""
    
    carriers = {
        '9075': 'Reliance Jio', '9074': 'Reliance Jio', '9072': 'Reliance Jio',
        '8606': 'Reliance Jio', '8607': 'Reliance Jio', '8086': 'Reliance Jio',
        '9446': 'Airtel', '9447': 'Airtel', '9440': 'Airtel',
        '8547': 'Airtel', '8548': 'Airtel', '9846': 'Airtel',
        '9656': 'Vodafone Idea', '9657': 'Vodafone Idea', '9633': 'Vodafone Idea',
        '7902': 'BSNL', '7903': 'BSNL', '9449': 'BSNL'
    }
    for p, c in carriers.items():
        if prefix.startswith(p) or p.startswith(prefix):
            info["carrier"] = c
            break
    
    locations = {
        '9075': 'Kerala', '9074': 'Kerala', '9072': 'Kerala',
        '9446': 'Kerala', '9447': 'Kerala', '9440': 'Kerala',
        '8606': 'Kerala', '8607': 'Kerala', '8086': 'Kerala',
        '9846': 'Karnataka', '8547': 'Karnataka', '8548': 'Karnataka',
        '9656': 'Tamil Nadu', '9657': 'Tamil Nadu', '9633': 'Tamil Nadu',
        '7902': 'Kerala', '7903': 'Kerala', '9449': 'Kerala'
    }
    info["location"] = locations.get(prefix, "India (Unknown Circle)")
    
    return info

async def lookup_phone_async(phone: str) -> dict:
    """Core async lookup function. Returns a dict with results."""
    phone = clean_phone(phone)
    result = {
        "phone": phone,
        "found": False,
        "error": None,
        "data": {}
    }
    
    if not API_ID or not API_HASH:
        result["error"] = "API credentials not configured"
        return result
    
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    
    try:
        await client.start()
        
        import_result = await client(functions.contacts.ImportContactsRequest(
            contacts=[types.InputPhoneContact(
                client_id=0,
                phone=phone,
                first_name="OSINT",
                last_name=""
            )]
        ))
        
        if import_result.users:
            user = import_result.users[0]
            
            # Fetch full profile
            full_info = None
            try:
                full_info = await client(functions.users.GetFullUserRequest(id=user.id))
            except:
                pass
            
            # Profile photo info
            photo_date = None
            try:
                photos = await client.get_profile_photos(user.id)
                if photos:
                    photo_date = photos[0].date.strftime('%Y-%m-%d') if hasattr(photos[0], 'date') else 'available'
            except:
                pass
            
            result["found"] = True
            result["data"] = {
                "user_id": user.id,
                "first_name": user.first_name or "",
                "last_name": user.last_name or "",
                "username": user.username,
                "phone_visible": user.phone or "Hidden by privacy",
                "bio": full_info.full_user.about if full_info and full_info.full_user.about else "",
                "is_bot": user.bot,
                "is_verified": user.verified,
                "is_premium": user.premium,
                "is_scam": user.scam,
                "is_fake": user.fake,
                "common_chats": full_info.full_user.common_chats_count if full_info else 0,
                "profile_photo": f"Available (uploaded {photo_date})" if photo_date else "None",
                "telegram_link": f"https://t.me/{user.username}" if user.username else f"https://t.me/{phone.replace('+', '')}",
                "whatsapp_link": f"https://wa.me/{phone.replace('+', '')}",
                "truecaller_link": f"https://www.truecaller.com/search/in/{phone.replace('+', '')}"
            }
            
            # Add India-specific info
            if phone.startswith('+91'):
                indian_info = _get_indian_info(phone)
                result["data"]["carrier"] = indian_info["carrier"]
                result["data"]["location"] = indian_info["location"]
            
            # Delete temp contact
            await client(functions.contacts.DeleteContactsRequest(id=[user.id]))
        else:
            result["data"] = {
                "telegram_link": f"https://t.me/{phone.replace('+', '')}",
                "whatsapp_link": f"https://wa.me/{phone.replace('+', '')}"
            }
            
    except FloodWaitError as e:
        result["error"] = f"Rate limited. Wait {e.seconds}s"
    except RPCError as e:
        result["error"] = f"Telegram API error: {e}"
    except Exception as e:
        result["error"] = str(e)
    finally:
        await client.disconnect()
    
    return result

def lookup_phone(phone: str) -> dict:
    """Synchronous wrapper for the async lookup."""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(lookup_phone_async(phone))
    finally:
        loop.close()
