"""Generate local sandbox credentials and deploy the Linux container stack."""
import argparse
import os
import secrets
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["up", "down", "status", "logs", "credentials", "seed", "configure"], nargs="?", default="up")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    env = root / "deployment/.env"
    if not env.exists():
        if args.action not in ("up", "configure"):
            parser.error("No deployment configuration exists. Run configure or up first.")
        descriptor = os.open(env, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w") as output:
            for name in ("GROCERY_SECRET_KEY", "POSTGRES_PASSWORD", "GROCERY_ADMIN_PASSWORD", "GROCERY_DEMO_PASSWORD", "GROCERY_PAYMENT_TOKEN"):
                output.write(f"{name}={secrets.token_urlsafe(36)}\n")
            output.write("GROCERY_PORT=8080\n")
        print("Created deployment/.env. Keep this private; credentials are not committed.")
    if args.action == "configure":
        return
    if args.action == "credentials":
        values = dict(line.split("=", 1) for line in env.read_text().splitlines() if "=" in line)
        print("Administrator: admin\nPassword: " + values["GROCERY_ADMIN_PASSWORD"])
        print("Demo accounts: customer, manager-east, manager-harbour\nPassword: " + values["GROCERY_DEMO_PASSWORD"])
        return
    compose = ["docker", "compose", "--env-file", str(env), "-f", str(root / "deployment/compose.yaml")]
    commands = {"up": ["up", "--build", "-d", "--wait", "--wait-timeout", "240"],
                "down": ["down"], "status": ["ps"], "logs": ["logs", "--tail", "100"],
                "seed": ["exec", "web-a", "python", "manage.py", "seed_demo"]}
    subprocess.run(compose + commands[args.action], check=True, cwd=root)
    if args.action == "up":
        print("Open http://localhost:8080. Run: python tools/deploy.py credentials")
        print("Sample stores and demo accounts are initialized automatically on an empty catalog.")


if __name__ == "__main__":
    main()
