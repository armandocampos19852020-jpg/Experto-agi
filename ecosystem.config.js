module.exports = {
  apps: [
    {
      name: "cosmos-pitbull-sentry",
      script: "cosmos_pitbull_sentry.py",
      interpreter: "python3",
      watch: false,
      autorestart: true,
      restart_delay: 5000,
      env: {
        TOKEN: process.env.TOKEN || "",
        REPO_OWNER: process.env.REPO_OWNER || "",
        REPO_NAME: process.env.REPO_NAME || "",
        HOOK_ID: process.env.HOOK_ID || "",
        NVIDIA_API_KEY: process.env.NVIDIA_API_KEY || "",
        NVIDIA_COSMOS_URL:
          process.env.NVIDIA_COSMOS_URL ||
          "https://api.nvidia.com/v1/cosmos/reasoning",
        POLL_SECONDS: process.env.POLL_SECONDS || "300",
      },
    },
  ],
};
