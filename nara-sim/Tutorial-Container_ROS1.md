# Tutorial de Uso do Container

## Montando a imagem no sistema

Primeiro é necessário baixar a imagem pelo link a seguir:

```
https://drive.google.com/drive/folders/1NVPu8TI2AMZITjuHpJ0YXWyKdt8hZNFw
```

Agora precisamos de duas coisas

1) Para rodar certos comandos sem usar sudo, precisamos linkar os terminais com o grupo "docker". Podemos fazer isso de forma íntegra ou temporária:

1.1) O comando seguinte adicionará o usuário de forma permanente no grupo, mas é necessário sair e voltar na sessão do Ubuntu.

```
bash
$ sudo usermod -aG docker $USER
```

1.2) Este comando forçará a entrada no grupo docker apenas no terminal ativo com resultado imediato, mas toda vez que for rodar o container precisará fazê-lo novamente.

```
bash
$ newgrp docker
```

Com a imagem *baixada e extraida* no local desejado, movimente-se pelo terminal para a pasta que contém o arquivo .tar com o comando cd

Normalmente estará aqui:

```
bash
$ cd ~/Downloads/Docker\ Nara/
```

Na pasta, rode o seguinte comando:

```
bash
$ docker load -i nara_noetic.tar
```

Isto carregará a *imagem* no sistema, ou seja, o template do container.

Por último, mas não menos importante, iremos rodar o container dando a ele o acesso da interface gráfica do computador, então:

```
bash
$ xhost +local:docker
```

Este comando permite que containers interajam com a interface gráfica, display do sistema Linux. Então, resta rodar o container com a interface ativa:

```
bash
$ docker run -it \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
  --device /dev/dri \
  --name nara_noetic \
  nara_noetic:2.0
```

Para abrir um novo terminal no container rodando, faça:

```
bash
$ docker exec -it nara_noetic bash
```

o nome do container será dado pela seguinte linha de comando do docker run modificável:
--name nara_noetic
Se apagar essa linha o container terá um nome aleatório que pode ser verificado com o comando $ docker ps -a.




