import os
import subprocess
import sys
import readline

def main():
    root_dir = "/home/hamza/straw-distro"
    straw_bin = os.path.join(root_dir, "bin")
    straw_usr_bin = os.path.join(root_dir, "usr", "bin")
    
    # Strictly isolated PATH restricted only to Straw-Linux directories
    isolated_path = f"{straw_bin}:{straw_usr_bin}"

    while True:
        try:
            line = input("Straw-Linux:/# ").strip()

            if not line:
                continue

            if line == "exit":
                break

            env = os.environ.copy()
            env["PATH"] = isolated_path
            env["HOME"] = root_dir

            if line.startswith("pkg"):
                pkg_args = line[3:].strip().split()
                cmd = [sys.executable, os.path.join(root_dir, "bin/pkg.py")] + pkg_args
                use_shell = False
            else:
                cmd = line
                use_shell = True

            # Executes commands directly in the container with native terminal attachment
            subprocess.run(
                cmd,
                shell=use_shell,
                cwd=root_dir,
                env=env
            )

        except KeyboardInterrupt:
            print("\nUse 'exit' to quit.")
        except Exception as e:
            print(f"Error executing command: {e}")

if __name__ == "__main__":
    main()
