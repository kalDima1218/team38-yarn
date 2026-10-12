# Развёртывание Hadoop / YARN — team-38

Учебный стенд. Инструкция и автоматизированные скрипты.
Дата выполнения: 11 октября 2026 года, время в итоговом отчёте — московское.

## 1. ЧТО В КОМПЛЕКТЕ

| Файл | Назначение |
| --- | --- |
| `scripts/deploy.sh` | Полный запуск установки, конфигурации и проверок. |
| `scripts/bootstrap.sh` | Java 17 и Hadoop 3.5.0, проверка SHA-512. |
| `scripts/generate.py` | Генерация конфигураций для каждого узла. |
| `scripts/install-config.sh` | Установка конфигураций и systemd-служб. |
| `scripts/single-node.sh` | Отдельное одноузловое развёртывание и WordCount. |
| `scripts/start-cluster.sh` | Запуск итогового многонодового кластера. |
| `scripts/publish.sh` | Публикация всех веб-интерфейсов через Nginx. |
| `scripts/smoke.sh` | WordCount, Hadoop Streaming, отчёты YARN/HDFS. |
| `scripts/assert-cluster.py` | Проверка числа узлов и репликации тестовых блоков. |
| `scripts/verify-access.py` | Внешняя проверка UIs/API и скачивания WebHDFS. |
| `scripts/verify-live-proxy.py` | Проверка живого Application Master через WebProxy. |
| `scripts/wait-ready.py` | Событийное ожидание готовности по изменениям логов. |
| `scripts/access.sh` | Доступ с внешнего компьютера по SSH-туннелю. |
| `scripts/cloud-publish.sh` | Дополнительная HTTPS-публикация через Cloudflare. |
| `scripts/cloud-publish.py` | Создание служб туннелей и сбор публичных адресов. |
| `examples/` | Mapper и reducer для Hadoop Streaming. |
| `generated/` | Конфигурации каждого узла, systemd и Nginx. |
| `evidence/` | Журналы и результаты проверок. |
| `REPORT.md` | Итоговый отчёт с результатами и ссылками. |

Приватные SSH-ключи в комплект не включены. Нужен уже разрешённый ключ
пользователя team для edge; внутренний ключ существует на самом edge.

## 2. ТОПОЛОГИЯ

Внешний SSH: `team@178.236.27.140`.

| Узел | IP | Службы |
| --- | --- | --- |
| `team-38-en` | `10.38.0.10` | Клиент, Nginx, SecondaryNameNode, JobHistory, Timeline / Application History, Web Application Proxy |
| `team-38-nn` | `10.38.0.11` | NameNode, ResourceManager |
| `team-38-00` | `10.38.0.12` | DataNode, NodeManager |
| `team-38-01` | `10.38.0.13` | DataNode, NodeManager |

На каждом узле Ubuntu 24.04, 2 vCPU, около 4 ГБ RAM и диск около 48 ГБ.
Используются Apache Hadoop 3.5.0 и OpenJDK 17.
Порты RPC HDFS/YARN остаются внутри сети кластера.

## 3. ПОЛНОЕ АВТОМАТИЗИРОВАННОЕ РАЗВЁРТЫВАНИЕ

На внешнем компьютере, где установлен ssh/scp, подготовить свой ключ:

```bash
chmod 600 /path/to/your/key
scp -i /path/to/your/key team38-yarn-submission.zip team@178.236.27.140:/home/team/
ssh -i /path/to/your/key team@178.236.27.140
```

На edge распаковать архив. Если unzip отсутствует, можно распаковать Python:

```bash
python3 -m zipfile -e /home/team/team38-yarn-submission.zip /home/team/
cd /home/team/team38-yarn
bash scripts/deploy.sh
```

Скрипты запускаются от team, административные операции используют sudo.
Пароль sudo на выданном стенде не требуется.
На внутренние узлы скрипты переходят через ~/.ssh/team_internal.
Для первоначального подтверждения новых внутренних SSH-хостов используется
StrictHostKeyChecking=accept-new; изменившиеся ключи хостов не принимаются.

Установка скачивает один архив Hadoop на edge, проверяет официальный SHA-512,
затем передаёт архив на внутренние узлы. До запуска везде устанавливается Java.
Скрипт исправляет /etc/hosts: каждое имя team-38-* связано только с его
внутренним IP. Исходный hosts сохраняется в /etc/hosts.pre-yarn.
Привязка имени узла к 127.0.1.1 приводит к недоступным извне узла RPC-службам.

Первый запуск проверяет отдельный одноузловой вариант, останавливает его,
поднимает многонодовый кластер, Nginx и запускает интеграционные проверки.
После успешной одноузловой проверки создаётся маркер:

```text
/home/team/yarn-lab/logs/single-node.passed
```

Повторный deploy.sh автоматически пропускает уже проверенную демонстрацию.
RUN_SINGLE_DEMO=0 отключает её явно; RUN_SINGLE_DEMO=1 запускает явно.
Перед повторной одноузловой демонстрацией надо остановить службы edge,
которые используют те же порты. Итоговый многонодовый HDFS не удаляется.

## 4. КОНФИГУРАЦИОННЫЕ ФАЙЛЫ

Конфигурация итогового кластера расположена в /etc/hadoop на всех узлах.
Конфигурация отдельной демонстрации — /etc/hadoop-single только на edge.
При установке копируются стандартные файлы из дистрибутива Hadoop, затем
применяются явно сгенерированные файлы. Это сохраняет log4j.properties,
hadoop-metrics2.properties и прочие необходимые стандартные настройки.

### `core-site.xml`

- fs.defaultFS=hdfs://team-38-nn:9000 — адрес HDFS для клиентов и служб;
- hadoop.tmp.dir=/var/lib/hadoop/tmp — локальные временные данные;
- hadoop.http.staticuser.user=team — пользователь чтения веб-интерфейса.

### `hdfs-site.xml`

- dfs.replication=2 — два экземпляра блоков на двух рабочих узлах;
- dfs.namenode.name.dir — каталог метаданных NameNode;
- dfs.datanode.data.dir — каталог блоков DataNode;
- dfs.namenode.rpc-address и http-address — RPC и веб-интерфейс NameNode;
- dfs.namenode.secondary.http-address — интерфейс SecondaryNameNode;
- dfs.namenode.checkpoint.dir и period — каталог и период checkpoint;
- dfs.datanode.address, ipc.address, http.address — адреса конкретного DataNode;
- dfs.webhdfs.enabled=true — WebHDFS, в том числе просмотр данных через UI;
- dfs.client.use.datanode.hostname=true — адреса DataNode по именам.

### `yarn-site.xml`

- yarn.resourcemanager.hostname=team-38-nn — координатор ресурсов;
- yarn.nodemanager.hostname — имя соответствующего рабочего узла;
- yarn.nodemanager.aux-services=mapreduce_shuffle — обмен результатами map;
- yarn.nodemanager.env-whitelist — переменные среды, доступные контейнерам;
- yarn.nodemanager.resource.memory-mb=2048, cpu-vcores=2 — ресурсы одного NM;
- scheduler minimum=256 МБ, maximum=2048 МБ — допустимые размеры контейнеров;
- yarn.nodemanager.vmem-check-enabled=false — виртуальная память JVM может значительно превышать реально занятую физическую память;
- yarn.log-aggregation-enable=true — сбор логов контейнеров в HDFS;
- yarn.nodemanager.remote-app-log-dir=/tmp/logs — агрегированные логи;
- yarn.log.server.url — переход к логам через JobHistory;
- yarn.web-proxy.address=team-38-en:9099 — отдельный Web Application Proxy;
- yarn.timeline-service.enabled=true, version=1.0 — Timeline Service v1 с локальным LevelDB и Application History, без отдельного HBase-кластера;
- yarn.system-metrics-publisher.enabled=true — RM передаёт события приложений в Timeline, включено восстановление состояния Timeline.

### `mapred-site.xml`

- mapreduce.framework.name=yarn — задания выполняются через YARN;
- mapreduce.application.classpath — библиотеки MapReduce;
- mapreduce.jobhistory.address и webapp.address — RPC и UI JobHistory;
- intermediate-done-dir=/mr-history/tmp, done-dir=/mr-history/done — история;
- Application Master, map и reduce получают по 512 МБ, heap JVM — 384 МБ;
- включено восстановление состояния JobHistory через локальный LevelDB.

### `capacity-scheduler.xml`

- очередь root.default получает 100% ресурса, допускает подачу заданий;
- maximum-am-resource-percent=0.5 позволяет запуск AM на маленьком стенде.

### `hadoop-env.sh`

- JAVA_HOME, пути Hadoop, каталоги логов и ограничение heap для каждого демона.
- Для hadoop включены файлы логов и системный журнал; клиент team пишет в
- консоль и не пытается писать в закрытые служебные файлы логов.

yarn-env.sh и mapred-env.sh используют настройки hadoop-env.sh.
workers содержит team-38-00 и team-38-01.

## 5. ОДНОУЗЛОВОЙ ВАРИАНТ

Для него все четыре основные службы работают на team-38-en:
NameNode, DataNode, ResourceManager и NodeManager.
Конфигурация /etc/hadoop-single указывает fs.defaultFS на team-38-en:9000,
dfs.replication=1, workers=team-38-en.
Данные находятся в /var/lib/hadoop/single, логи — /var/log/hadoop/single.
systemd-службы имеют имена hadoop-single-*.service.

```bash
bash scripts/single-node.sh
```

Скрипт выполняет WordCount и проверяет результат через diff, показывает
один RUNNING NodeManager и один живой DataNode, затем останавливает демоны.
Данные демонстрации сохраняются отдельно от многонодового кластера.
NameNode форматируется только при отсутствии VERSION, проверяемом от
имени hadoop. Флаги принудительного форматирования не используются.

## 6. ВЕБ-ИНТЕРФЕЙСЫ

| Служба | Внутренний адрес | Порт Nginx на edge |
| --- | --- | --- |
| ResourceManager | team-38-nn:8088 | 18088 |
| NodeManager 0 | team-38-00:8042 | 18042 |
| NodeManager 1 | team-38-01:8042 | 18043 |
| MapReduce JobHistory | team-38-en:19888 | 19880 |
| Timeline / Application History team-38-en:8188 | 18188 |
| Web Application Proxy | team-38-en:9099 | 19099 |
| HDFS NameNode | team-38-nn:9870 | 19870 |
| HDFS DataNode 0 | team-38-00:9864 | 19864 |
| HDFS DataNode 1 | team-38-01:9864 | 19865 |
| HDFS SecondaryNameNode | team-38-en:9868 | 19868 |
| Общая страница со ссылками | Nginx на edge | 80 |

Nginx публикует каждый сервис в корне отдельного порта. Поэтому пути
статических ресурсов и API сохраняются, а внутренние адреса в HTML/JSON
и Location заменяются адресами внешних интерфейсов.
В проксируемых интерфейсах разрешены GET/HEAD; методы изменения состояния
через опубликованный gateway заблокированы.

У Web Application Proxy нет собственной страницы со списком приложений.
На его корне размещена поясняющая страница. Настоящий интерфейс Application
Master доступен по /proxy/application_.../ только для соответствующего
приложения. Завершённые MapReduce-задания смотрят через JobHistory.
SecondaryNameNode создаёт checkpoint; это не резервный NameNode и не HA.

## 7. ДОСТУП С ВНЕШНЕГО КОМПЬЮТЕРА

На данном стенде внешний SSH доступен, но внешний TCP/80 завершается
таймаутом при работающем Nginx и отсутствии локального firewall.
Открытие ingress-портов требует изменения правил вне виртуальной машины.
Если администратор разрешит нужные порты, прямой портал будет доступен:
[http://178.236.27.140/](http://178.236.27.140/)

Интерфейсы — http://178.236.27.140:ПОРТ_ИЗ_ТАБЛИЦЫ/.

Рабочий независимый от этих ingress-портов вариант — SSH:

```bash
bash scripts/access.sh /path/to/your/ssh_private_key
```

На Mac можно автоматически открыть браузер при подключении:

```bash
OPEN_BROWSER=1 bash scripts/access.sh /path/to/your/ssh_private_key
```

Оставить этот терминал открытым, в браузере открыть:
[http://127.0.0.1:18080/](http://127.0.0.1:18080/)

или нужный UI, например http://127.0.0.1:18088/cluster.
Внешний пользователь подключается к опубликованным веб-службам через
шифрованный SSH-канал. Завершение ssh закрывает локальные перенаправления.

Дополнительная публикация через Cloudflare (на стенде не запускалась):

```bash
bash scripts/cloud-publish.sh
cat public-links.json
```

Скрипт создаёт отдельные tunnel services и переписывает Nginx/портал под
HTTPS-адреса. Ключи SSH провайдеру не передаются. Провайдер обслуживает
веб-трафик и имеет доступ к публикуемому содержимому интерфейсов.
Quick Tunnel предназначен для учебной демонстрации и не гарантирует uptime.
Туннели не перезапускаются автоматически и не включены в автозагрузку:
каждый запуск создаёт новый домен и требует обновления всех ссылок.
Скрипт останавливает прошлые туннели, очищает только их журналы и ждёт
регистрацию каждого нового запуска по событиям записи в журнал.
После падения туннеля или перезагрузки edge снова выполнить
cloud-publish.sh и использовать актуальные ссылки из public-links.json.
Для постоянного домена нужны именованный туннель/домен либо разрешённые
облачные ingress-порты. Внешние результаты проверок приведены в REPORT.md.

## 8. ПРОВЕРКА РАБОТЫ

На edge:

```bash
source /etc/profile.d/hadoop.sh
yarn node -list
bash scripts/smoke.sh
```

В многонодовом варианте yarn node -list должен показать два узла RUNNING.
smoke.sh создаёт уникальный входной каталог в /user/team, выполняет настоящий
MapReduce WordCount и Hadoop Streaming с Python mapper/reducer и сравнивает
результат каждого задания с эталоном. Затем проверяет точное число
RUNNING NodeManager и живых DataNode, отсутствие повреждённых/потерянных
блоков и фактическую репликацию тестовых файлов через fsck (2 для основного
кластера, 1 для одноузлового):

```text
hadoop  1
hello   2
yarn    1
```

Административный отчёт HDFS запускается отдельно от имени hadoop:

```bash
sudo -u hadoop /opt/hadoop/bin/hdfs --config /etc/hadoop dfsadmin -report
```

Должны быть два Live datanodes, без потерянных и повреждённых блоков.
В JobHistory должно появиться завершённое задание с успешными map/reduce.
С внешнего компьютера (локальные порты должны быть свободны):

```bash
python3 scripts/verify-access.py /path/to/your/key evidence/check.json
```

Проверка сама открывает SSH-канал, получает реальные страницы/API всех служб,
проверяет историю заданий, переход WebProxy и скачивание файла через
NameNode → DataNode, затем закрывает канал.

Проверка интерфейса работающего Application Master на edge:

```bash
python3 scripts/verify-live-proxy.py evidence/live-proxy.json
```

Она запускает WordCount и по событию прогресса задания получает его настоящий
интерфейс через WebProxy, затем проверяет успешное завершение и результат.

Для логов выполнить на edge:

```bash
yarn logs -applicationId application_...
```

## 9. УПРАВЛЕНИЕ И ДИАГНОСТИКА

Службы systemd включены в автозагрузку и работают от пользователя hadoop.
Например на master:

```bash
sudo systemctl status hadoop-namenode hadoop-resourcemanager
```

На worker:

```bash
sudo systemctl status hadoop-datanode hadoop-nodemanager
```

На edge:

```bash
sudo systemctl status hadoop-secondarynamenode hadoop-historyserver hadoop-timelineserver hadoop-proxyserver nginx
```

Системный журнал:

```bash
sudo journalctl -u hadoop-resourcemanager -n 80 --no-pager
```

Служебные логи:

```text
/var/log/hadoop/hadoop.log
```

Логи установки и тестов:

```text
/home/team/yarn-lab/logs/
```

Проверка Nginx:

```bash
sudo nginx -t
```

Службы используют Restart=on-failure, ограничения памяти и файловых
дескрипторов. Ограничение NodeManager включает его дочерние контейнеры,
поэтому MemoryMax для NM выше суммарного выделяемого ресурса контейнеров.
Готовность служб проверяется по изменениям журналов через inotify.
При ошибке запуска причину следует искать в журнале соответствующей службы.

Перед ручным перезапуском убедиться, что нет нужного выполняющегося задания.
Изменённые настройки Hadoop применяются после перезапуска соответствующих
служб. Публичные URL в Nginx меняются после generate.py и publish.sh.
Повторная установка не удаляет данные HDFS и не форматирует существующий NN.
Это учебный non-HA кластер в изолированной сети, без Kerberos.

## 10. ОФИЦИАЛЬНЫЕ ИСТОЧНИКИ

- [Apache Hadoop 3.5.0 / Java 17](https://hadoop.apache.org/docs/r3.5.0/)
- [Single Node Setup](https://hadoop.apache.org/docs/r3.5.0/hadoop-project-dist/hadoop-common/SingleCluster.html)
- [Cluster Setup](https://hadoop.apache.org/docs/r3.5.0/hadoop-project-dist/hadoop-common/ClusterSetup.html)
- [YARN architecture](https://hadoop.apache.org/docs/r3.5.0/hadoop-yarn/hadoop-yarn-site/YARN.html)
- [Web Application Proxy](https://hadoop.apache.org/docs/r3.5.0/hadoop-yarn/hadoop-yarn-site/WebApplicationProxy.html)
- [Timeline Server](https://hadoop.apache.org/docs/r3.5.0/hadoop-yarn/hadoop-yarn-site/TimelineServer.html)
- [Cloudflare Quick Tunnels](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/)
