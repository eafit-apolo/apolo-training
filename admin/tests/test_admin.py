"""alta, baja y archivar contra comandos y plataforma simulados (ver conftest.py)."""

import datetime
import os
import tarfile

import apolo_training_admin as admin
from conftest import TOKEN

ALTA = (
    "alta",
    "ana",
    "--cluster",
    "apolo2",
    "--nombre",
    "Ana Pérez",
    "--correo",
    "ana@example.org",
)


def clave_de_chpasswd(comandos):
    (llamada,) = [x for x in comandos.llamadas() if x["cmd"][0] == "chpasswd"]
    usuario, clave = llamada["entrada"].strip().split(":", 1)
    return usuario, clave


# --- alta -------------------------------------------------------------------


def test_alta_crea_todo_con_la_misma_clave(correr, comandos, plataforma, conf):
    r = correr(*ALTA)

    assert r.codigo == 0, r.error
    assert comandos.nombres() == [
        "useradd",
        "chpasswd",
        "chage",
        "sacctmgr add",
        "runuser",
    ]
    llamadas = {x["cmd"][0]: x["cmd"] for x in comandos.llamadas()}
    assert llamadas["useradd"] == [
        "useradd",
        "-m",
        "-G",
        "apolo2",
        "-c",
        "Ana Pérez",
        "ana",
    ]
    assert llamadas["chage"] == ["chage", "-d", "0", "ana"]
    assert "Account=curso-apolo2" in llamadas["sacctmgr"]
    assert llamadas["runuser"][-2:] == [
        str(conf.verificador / "bin" / "apolo-training"),
        "preparar",
    ]
    assert (conf.perfiles / "ana").read_text() == "apolo2\n"

    usuario, clave = clave_de_chpasswd(comandos)
    (pedido,) = plataforma.pedidos
    assert pedido["metodo"] == "POST"
    assert pedido["ruta"] == "/api/internal/usuarios"
    assert pedido["auth"] == f"Bearer {TOKEN}"
    assert pedido["cuerpo"] == {
        "username": "ana",
        "nombre": "Ana Pérez",
        "correo": "ana@example.org",
        "cluster": "apolo2",
        "clave_temporal": clave,
    }
    assert usuario == "ana"
    assert clave in r.salida  # el administrador se la entrega al usuario
    assert clave not in " ".join(" ".join(x["cmd"]) for x in comandos.llamadas())


def test_alta_apolo3_e_idioma(correr, comandos, plataforma, conf):
    r = correr(
        "alta", "beto", "--cluster", "apolo3", "--nombre", "Beto",
        "--correo", "b@example.org", "--idioma", "en",
    )  # fmt: skip

    assert r.codigo == 0, r.error
    sacctmgr = next(x["cmd"] for x in comandos.llamadas() if x["cmd"][0] == "sacctmgr")
    assert "Account=curso-apolo3" in sacctmgr
    assert (conf.perfiles / "beto").read_text() == "apolo3\n"
    assert plataforma.pedidos[0]["cuerpo"]["idioma"] == "en"


def test_alta_revierte_si_la_plataforma_responde_409(
    correr, comandos, plataforma, conf
):
    plataforma.responder(409, {"detail": "ya existe", "codigo": "usuario_existe"})

    r = correr(*ALTA)

    assert r.codigo == 1
    assert "usuario_existe" in r.error
    assert "se revirtió" in r.error
    # Lo de la VM se deshace en orden inverso: Slurm antes que la cuenta
    assert comandos.nombres()[-2:] == ["sacctmgr delete", "userdel"]
    assert comandos.llamadas()[-1]["cmd"] == ["userdel", "-r", "ana"]
    assert not (conf.perfiles / "ana").exists()


def test_alta_revierte_si_la_plataforma_no_responde(correr, comandos, conf):
    conf.escribir(url="http://127.0.0.1:9/api")  # puerto discard: conexión rechazada

    r = correr(*ALTA)

    assert r.codigo == 1
    assert "sin_conexion" in r.error
    assert comandos.nombres()[-2:] == ["sacctmgr delete", "userdel"]
    assert not (conf.perfiles / "ana").exists()


def test_alta_revierte_lo_hecho_hasta_el_paso_que_falla(
    correr, comandos, plataforma, monkeypatch
):
    monkeypatch.setenv("FALSO_CODIGO_SACCTMGR", "1")
    monkeypatch.setenv("FALSO_SALIDA_SACCTMGR", "Account curso-apolo2 no existe")

    r = correr(*ALTA)

    assert r.codigo == 1
    assert "curso-apolo2 no existe" in r.error
    assert comandos.nombres() == [
        "useradd",
        "chpasswd",
        "chage",
        "sacctmgr add",
        "userdel",
    ]
    assert plataforma.pedidos == []


def test_alta_avisa_si_la_reversion_queda_incompleta(correr, plataforma, monkeypatch):
    plataforma.responder(500, {"detail": "boom", "codigo": "interno"})
    monkeypatch.setenv("FALSO_CODIGO_USERDEL", "8")
    monkeypatch.setenv(
        "FALSO_SALIDA_USERDEL", "user ana is currently used by process 42"
    )

    r = correr(*ALTA)

    assert r.codigo == 1
    assert "reversión quedó incompleta" in r.error
    assert "borrar la cuenta Unix" in r.error


def test_alta_no_toca_nada_si_el_usuario_ya_existe(correr, comandos, plataforma, vm):
    vm.usuarios.add("ana")

    r = correr(*ALTA)

    assert r.codigo == 1
    assert "ya existe" in r.error
    assert comandos.llamadas() == []
    assert plataforma.pedidos == []


def test_alta_exige_token_solo_de_root(correr, comandos, conf):
    conf.token.chmod(0o644)

    r = correr(*ALTA)

    assert r.codigo == 1
    assert "chmod 600" in r.error
    assert comandos.llamadas() == []


def test_alta_exige_https(correr, comandos, conf):
    conf.escribir(url="http://plataforma.example.org/api")

    r = correr(*ALTA)

    assert r.codigo == 1
    assert "https" in r.error
    assert comandos.llamadas() == []


def test_alta_exige_el_verificador(correr, comandos, conf):
    conf.escribir(verificador="/no/existe")

    r = correr(*ALTA)

    assert r.codigo == 1
    assert "verificador" in r.error
    assert comandos.llamadas() == []


def test_alta_valida_los_datos(correr, comandos):
    malos = [
        ("Ana", "Ana", "a@example.org"),  # mayúsculas
        ("ana", "Pérez, Ana", "a@example.org"),  # coma en el GECOS
        ("ana", "Ana", "no-es-correo"),
    ]
    for usuario, nombre, correo in malos:
        r = correr(
            "alta",
            usuario,
            "--cluster",
            "apolo2",
            "--nombre",
            nombre,
            "--correo",
            correo,
        )
        assert r.codigo == 1, (usuario, nombre, correo)
    assert comandos.llamadas() == []


def test_solo_root(correr, comandos, monkeypatch):
    monkeypatch.setattr(admin, "es_root", lambda: False)

    r = correr(*ALTA)

    assert r.codigo == 1
    assert "root" in r.error
    assert comandos.llamadas() == []


def test_clave_temporal():
    claves = {admin.clave_temporal() for _ in range(200)}
    assert len(claves) == 200
    for clave in claves:
        assert len(clave) == admin.LARGO_CLAVE
        assert not set(clave) & set("0O1lI")
        assert any(c.isupper() for c in clave)
        assert any(c.islower() for c in clave)
        assert any(c.isdigit() for c in clave)


# --- baja -------------------------------------------------------------------


def test_baja_bloquea_vm_slurm_y_plataforma(correr, comandos, plataforma, conf, vm):
    vm.usuarios.add("ana")
    vm.del_curso.add("ana")
    plataforma.responder(200, {})

    r = correr("baja", "ana")

    assert r.codigo == 0, r.error
    assert [x["cmd"] for x in comandos.llamadas()] == [
        ["usermod", "-L", "-e", "1", "ana"],
        ["pkill", "-KILL", "-u", "ana"],
        ["scancel", "-u", "ana"],
        ["sacctmgr", "-i", "delete", "user", "ana"],
    ]
    (pedido,) = plataforma.pedidos
    assert pedido["metodo"] == "PATCH"
    assert pedido["ruta"] == "/api/internal/usuarios/ana"
    assert pedido["cuerpo"] == {"activo": False}
    assert (conf.bajas / "ana").read_text().strip() == admin.hoy().isoformat()


def test_baja_repetida_conserva_la_fecha(correr, plataforma, conf, vm):
    vm.usuarios.add("ana")
    vm.del_curso.add("ana")
    conf.bajas.mkdir()
    (conf.bajas / "ana").write_text("2026-01-02\n")
    plataforma.responder(200, {})

    r = correr("baja", "ana")

    assert r.codigo == 0, r.error
    assert (conf.bajas / "ana").read_text() == "2026-01-02\n"


def test_baja_tolera_sin_asociacion_ni_procesos(correr, plataforma, vm, monkeypatch):
    vm.usuarios.add("ana")
    vm.del_curso.add("ana")
    monkeypatch.setenv("FALSO_CODIGO_PKILL", "1")
    monkeypatch.setenv("FALSO_CODIGO_SACCTMGR", "1")
    monkeypatch.setenv("FALSO_SALIDA_SACCTMGR", " Nothing deleted\n")
    plataforma.responder(200, {})

    r = correr("baja", "ana")

    assert r.codigo == 0, r.error


def test_baja_se_niega_con_quien_no_es_del_curso(correr, comandos, plataforma, vm):
    vm.usuarios.add("admin")

    r = correr("baja", "admin")

    assert r.codigo == 1
    assert "no es del curso" in r.error
    assert comandos.llamadas() == []
    assert plataforma.pedidos == []


def test_baja_si_falla_la_plataforma_la_vm_queda_bloqueada(
    correr, comandos, plataforma, vm
):
    vm.usuarios.add("ana")
    vm.del_curso.add("ana")
    plataforma.responder(503, {"detail": "mantenimiento", "codigo": "no_disponible"})

    r = correr("baja", "ana")

    assert r.codigo == 1
    assert "repetir la baja" in r.error
    assert comandos.llamadas()[0]["cmd"][:2] == ["usermod", "-L"]


def test_baja_sin_cuenta_en_la_plataforma(correr, plataforma, vm):
    vm.usuarios.add("ana")
    vm.del_curso.add("ana")
    plataforma.responder(404, {"detail": "no existe", "codigo": "no_encontrado"})

    r = correr("baja", "ana")

    assert r.codigo == 0, r.error
    assert "no existía en la plataforma" in r.error


def test_baja_solo_en_la_plataforma(correr, comandos, plataforma):
    plataforma.responder(200, {})

    r = correr("baja", "ana")

    assert r.codigo == 0, r.error
    assert comandos.llamadas() == []
    assert len(plataforma.pedidos) == 1


def test_baja_de_quien_no_existe_en_ningun_lado(correr, plataforma):
    plataforma.responder(404, {"detail": "no existe", "codigo": "no_encontrado"})

    r = correr("baja", "ana")

    assert r.codigo == 1
    assert "ni en la VM ni en la plataforma" in r.error


# --- archivar ---------------------------------------------------------------


def preparar_baja(conf, vm, tmp_path, usuario, dias):
    home = tmp_path / "home" / usuario
    (home / "apolo-training").mkdir(parents=True)
    (home / "apolo-training" / "curso.sh").write_text("#!/bin/bash\n")
    vm.homes[usuario] = str(home)
    conf.bajas.mkdir(exist_ok=True)
    fecha = admin.hoy() - datetime.timedelta(days=dias)
    (conf.bajas / usuario).write_text(fecha.isoformat() + "\n")
    conf.perfiles.mkdir(exist_ok=True)
    (conf.perfiles / usuario).write_text("apolo2\n")
    return home, fecha


def test_archivar_solo_las_bajas_de_30_dias(correr, conf, vm, tmp_path, monkeypatch):
    vieja, fecha = preparar_baja(conf, vm, tmp_path, "ana", 30)
    nueva, _ = preparar_baja(conf, vm, tmp_path, "beto", 29)
    monkeypatch.setenv("FALSO_SALIDA_GETENT", "ana:!$6$x:20000:0:99999:7::1:\n")

    r = correr("archivar")

    assert r.codigo == 0, r.error
    paquete = conf.archivo / f"ana-{fecha.isoformat()}.tar.gz"
    with tarfile.open(paquete) as tar:
        assert "ana/apolo-training/curso.sh" in tar.getnames()
    assert oct(os.stat(paquete).st_mode & 0o777) == "0o600"
    assert not vieja.exists()
    assert not (conf.bajas / "ana").exists()
    assert not (conf.perfiles / "ana").exists()
    # La baja de hace 29 días sigue igual
    assert nueva.exists()
    assert (conf.bajas / "beto").exists()


def test_archivar_no_toca_una_cuenta_reactivada(
    correr, conf, vm, tmp_path, monkeypatch
):
    home, _ = preparar_baja(conf, vm, tmp_path, "ana", 40)
    monkeypatch.setenv("FALSO_SALIDA_GETENT", "ana:$6$x:20000:0:99999:7:::\n")

    r = correr("archivar")

    assert r.codigo == 1
    assert "ya no está de baja" in r.error
    assert home.exists()
    assert (conf.bajas / "ana").exists()


def test_archivar_sin_bajas(correr):
    r = correr("archivar")

    assert r.codigo == 0
