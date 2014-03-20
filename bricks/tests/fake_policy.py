policy_data = """
{
      "admin": "role:admin",
      "admin_or_owner":  "is_admin:True or project_id:%(project_id)s",
      "admin_api": "is_admin:True",
      "default": "rule:admin_api",
      "brick:create": "",
      "brick:delete": "",
      "brick:update": "",
      "brick:status_update": "rule:admin_api",
      "brick:get_one": "",
      "brick:get_all": "",
      "brickconfig:create": "rule:admin_api",
      "brickconfig:delete": "rule:admin_api",
      "brickconfig:update": "rule:admin_api",
      "brickconfig:get_one": "",
      "brickconfig:get_all": ""
}
"""
