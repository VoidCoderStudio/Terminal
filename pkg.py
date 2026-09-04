import os
import sys
import urllib.request
import tarfile
import glob
import tempfile

REPO_URL = "https://VoidCoderStudio.github.io/straw-root/stable/aarch64/"
DEFAULT_ROOT = "PUT THE VIRTUAL FILESYSTEM HERE"

def extract_ar_pure_python(ar_path, extract_to):
    with open(ar_path, "rb") as f:
        magic = f.read(8)
        if magic != b"!<arch>\n":
            raise ValueError("Not a valid ar archive")
        
        while True:
            header = f.read(60)
            if len(header) < 60:
                break
            name = header[0:16].decode('utf-8', errors='ignore').strip().rstrip('/')
            try:
                size = int(header[48:58].decode('utf-8').strip())
            except ValueError:
                break
                
            content = f.read(size)
            if size % 2 != 0:
                f.read(1)
                
            out_path = os.path.join(extract_to, name)
            with open(out_path, "wb") as out:
                out.write(content)

def unpack_and_install_deb(deb_path, pkg_name, root_dir):
    tmp_extract_dir = tempfile.mkdtemp()
    installed_files = []
    bin_dir = os.path.join(root_dir, "bin")
    os.makedirs(bin_dir, exist_ok=True)
    
    try:
        extract_ar_pure_python(deb_path, tmp_extract_dir)
        data_archives = glob.glob(os.path.join(tmp_extract_dir, "data.tar.*"))
        if not data_archives:
            print("[!] Error: Data payload not found inside the .deb package.")
            return False
        data_archive = data_archives[0]
        
        with tarfile.open(data_archive, "r:*") as tar:
            for member in tar.getmembers():
                clean_name = member.name.lstrip('/')
                target_path = os.path.abspath(os.path.join(root_dir, clean_name))
                installed_files.append(target_path + "\n")
                tar.extract(member, path=root_dir)
                
                if member.isfile():
                    try:
                        os.chmod(target_path, 0o755)
                    except Exception:
                        pass
                    if any(p in clean_name for p in ["bin/", "sbin/"]):
                        base_name = os.path.basename(clean_name)
                        dest_bin = os.path.join(bin_dir, base_name)
                        with open(target_path, "rb") as src, open(dest_bin, "wb") as dst:
                            dst.write(src.read())
                        os.chmod(dest_bin, 0o755)
                        installed_files.append(dest_bin + "\n")
                        
        manifest_dir = os.path.join(root_dir, "etc/pkg/manifests")
        os.makedirs(manifest_dir, exist_ok=True)
        manifest_path = os.path.join(manifest_dir, f"{pkg_name}.files.txt")
        with open(manifest_path, "w") as f:
            f.writelines(installed_files)
            
        print(f"[+] Successfully unpacked and installed {pkg_name} from .deb into Straw-Linux!")
        return True
    finally:
        for f in glob.glob(os.path.join(tmp_extract_dir, "*")):
            try:
                os.remove(f)
            except Exception:
                pass
        try:
            os.rmdir(tmp_extract_dir)
        except Exception:
            pass

def install_package(pkg_name, root_dir=DEFAULT_ROOT):
    exts = [".deb", ".tar.gz", ".tar.xz"]
    pkg_url, ext = None, None
    
    print(f"[*] Starting 3-way check for package '{pkg_name}' (.deb -> .tar.gz -> .tar.xz)...")
    
    for e in exts:
        test_url = f"{REPO_URL}{pkg_name}{e}"
        print(f"    [Checking] Trying format {e} -> {test_url}")
        try:
            req = urllib.request.Request(test_url, method="HEAD")
            with urllib.request.urlopen(req) as response:
                if response.status == 200:
                    pkg_url = test_url
                    ext = e
                    print(f"    [+] Found valid archive as {e}")
                    break
        except Exception:
            continue
            
    if not pkg_url:
        print(f"[!] Error: Package '{pkg_name}' not found on server in any format.")
        return False
        
    tmp_dir = tempfile.mkdtemp()
    downloaded_file = os.path.join(tmp_dir, f"{pkg_name}{ext}")
    print(f"[*] Downloading {pkg_name}{ext}...")
    
    try:
        urllib.request.urlretrieve(pkg_url, downloaded_file)
    except Exception as e:
        print(f"[!] Error downloading package: {e}")
        return False
        
    try:
        if ext == ".deb":
            # Direct .deb installation without any compression wrappers
            return unpack_and_install_deb(downloaded_file, pkg_name, root_dir)
        else:
            # It's a tarball (.tar.gz or .tar.xz) containing a .deb file or raw binaries
            print(f"[*] Unzipping/extracting container archive {ext}...")
            extract_folder = os.path.join(tmp_dir, "extracted_contents")
            os.makedirs(extract_folder, exist_ok=True)
            
            with tarfile.open(downloaded_file, "r:*") as tar:
                tar.extractall(path=extract_folder)
                
            # Check if the extracted contents yielded a .deb package inside
            extracted_debs = glob.glob(os.path.join(extract_folder, "**", "*.deb"), recursive=True)
            if extracted_debs:
                found_deb = extracted_debs[0]
                print(f"[+] Extracted archive yielded package: {os.path.basename(found_deb)}")
                return unpack_and_install_deb(found_deb, pkg_name, root_dir)
            else:
                # Fallback if the tarball directly contains binaries instead of a .deb file
                installed_files = []
                bin_dir = os.path.join(root_dir, "bin")
                os.makedirs(bin_dir, exist_ok=True)
                
                with tarfile.open(downloaded_file, "r:*") as tar:
                    for member in tar.getmembers():
                        clean_name = member.name.lstrip('/')
                        target_path = os.path.abspath(os.path.join(root_dir, clean_name))
                        installed_files.append(target_path + "\n")
                        tar.extract(member, path=root_dir)
                        
                        if member.isfile():
                            try:
                                os.chmod(target_path, 0o755)
                            except Exception:
                                pass
                            base_name = os.path.basename(clean_name)
                            dest_bin = os.path.join(bin_dir, base_name)
                            with open(target_path, "rb") as src, open(dest_bin, "wb") as dst:
                                dst.write(src.read())
                            os.chmod(dest_bin, 0o755)
                            installed_files.append(dest_bin + "\n")
                            
                manifest_dir = os.path.join(root_dir, "etc/pkg/manifests")
                os.makedirs(manifest_dir, exist_ok=True)
                manifest_path = os.path.join(manifest_dir, f"{pkg_name}.files.txt")
                with open(manifest_path, "w") as f:
                    f.writelines(installed_files)
                    
                print(f"[+] Successfully unpacked tarball and installed {pkg_name}!")
                return True
                
    except Exception as e:
        print(f"[!] Error during extraction/installation: {e}")
        return False
        
    finally:
        for root, dirs, files in os.walk(tmp_dir, topdown=False):
            for f in files:
                try:
                    os.remove(os.path.join(root, f))
                except Exception:
                    pass
            for d in dirs:
                try:
                    os.rmdir(os.path.join(root, d))
                except Exception:
                    pass
        try:
            os.rmdir(tmp_dir)
        except Exception:
            pass

def uninstall_package(pkg_name, root_dir=DEFAULT_ROOT):
    manifest_path = os.path.join(root_dir, f"etc/pkg/manifests/{pkg_name}.files.txt")
    if not os.path.exists(manifest_path):
        print(f"[!] Error: Package '{pkg_name}' is not installed or missing its manifest.")
        return False

    print(f"[*] Removing files for {pkg_name}...")
    try:
        with open(manifest_path, "r") as f:
            files = f.readlines()
            
        for filepath in reversed(files):
            filepath = filepath.strip()
            if os.path.isfile(filepath):
                os.remove(filepath)
            elif os.path.isdir(filepath) and not os.listdir(filepath):
                os.rmdir(filepath)
                
        os.remove(manifest_path)
        print(f"[+] Successfully uninstalled {pkg_name}!")
        return True
    except Exception as e:
        print(f"[!] Error during uninstallation: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 pkg.py <install|uninstall> <package_name>")
        sys.exit(1)
        
    command = sys.argv[1].lower()
    pkg = sys.argv[2]
    
    if command == "install":
        install_package(pkg)
    elif command == "uninstall":
        uninstall_package(pkg)
    else:
        print(f"[!] Unknown command: {command}")
        sys.exit(1)
