import os
import json
import urllib.request
import urllib.error

GEN_13_MEMBERS = {
    "Nur Intan",
    "Jacqueline Immanuela",
    "Astrella Virgiananda",
    "Jemima Evodie",
    "Mikaela Kusjanto",
    "Aulia Riza",
    "Hagia Sopia",
    "Humaira Ramadhani",
    "Bong Aprilli"
}

def format_name(name):
    if name in GEN_13_MEMBERS:
        return name.replace(' ', '_')
    return name.lower().replace(' ', '_')

def download_images():
    os.makedirs('img', exist_ok=True)
    
    with open('data.json', 'r') as f:
        raw_data = json.load(f)
        
    # Specifically target the 'members' list from your JSON structure
    members_list = raw_data.get('members', [])
        
    opener = urllib.request.build_opener()
    opener.addheaders = [('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)')]
    urllib.request.install_opener(opener)
        
    for item in members_list:
        member_name = item.get('name')
            
        if not member_name:
            continue

        formatted = format_name(member_name)
        url = f"https://jkt48.com/api/v1/storages/media/jkt48-member/{formatted}.jpg"
        filepath = os.path.join('img', f"{formatted}.jpg")
        
        if not os.path.exists(filepath):
            try:
                urllib.request.urlretrieve(url, filepath)
            except urllib.error.URLError as e:
                print(f"Failed to download {formatted}.jpg: {e}")

if __name__ == "__main__":
    download_images()