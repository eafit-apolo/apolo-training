# ansible

Roles de la VM de práctica y de la plataforma. IPs, usuarios y contraseñas van
en Ansible Vault, nunca en claro.

| Archivo | Qué es |
| --- | --- |
| `inventory.ini` | Máquinas y usuario de conexión (**cifrado**) |
| `group_vars/all/vault.yml` | Admins, llaves, IPs y contraseña de sudo (**cifrado**) |
| `group_vars/*/vars.yml` | Variables; solo referencian las del Vault |
| `site.yml` | Qué rol se aplica a qué grupo |
| `roles/base` | Admins solo con llave y sshd sin root (contraseña solo para `apolo2` y `apolo3`) |

## Requisitos

- VPN activa, colecciones `ansible.posix` y `community.general`.
- `ansible/.vault_pass` información privada


## Uso

```bash
ansible-playbook site.yml --check --diff   # simular
ansible-playbook site.yml --diff           # aplicar (la segunda vez: changed=0)
ansible-vault edit group_vars/all/vault.yml   # agregar admins o llaves
```