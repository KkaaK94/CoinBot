module.exports = {
  apps: [
    {
      name: 'coinbot-main',
      script: '/home/ubuntu/venv/bin/python',
      args: '/home/ubuntu/upbit/CoinBot/main.py',
      cwd: '/home/ubuntu/upbit/CoinBot',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      restart_delay: 5000,
      env: {
        NODE_ENV: 'production',
        PYTHONPATH: '/home/ubuntu/upbit/CoinBot',
        PATH: '/home/ubuntu/venv/bin:' + process.env.PATH
      },
      error_file: '/home/ubuntu/upbit/CoinBot/data/logs/main_err.log',
      out_file: '/home/ubuntu/upbit/CoinBot/data/logs/main_out.log',
      log_file: '/home/ubuntu/upbit/CoinBot/data/logs/main_combined.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z'
    },
    {
      name: 'coinbot-dashboard',
      script: '/home/ubuntu/venv/bin/python',
      args: '/home/ubuntu/upbit/CoinBot/dashboard/web_dashboard.py',
      cwd: '/home/ubuntu/upbit/CoinBot',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '512M',
      restart_delay: 3000,
      env: {
        NODE_ENV: 'production',
        PYTHONPATH: '/home/ubuntu/upbit/CoinBot',
        PATH: '/home/ubuntu/venv/bin:' + process.env.PATH
      },
      error_file: '/home/ubuntu/upbit/CoinBot/data/logs/dashboard_err.log',
      out_file: '/home/ubuntu/upbit/CoinBot/data/logs/dashboard_out.log',
      log_file: '/home/ubuntu/upbit/CoinBot/data/logs/dashboard_combined.log'
    }
  ]
};
