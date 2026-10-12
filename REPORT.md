# Развёртывание Hadoop / YARN team-38

**Выполнено на предоставленных четырёх узлах.** Версии: Apache Hadoop 3.5.0, OpenJDK 17, Ubuntu 24.04. Итоговая проверка: 11.10.2026 14:05 МСК.

**Фактический внешний доступ:** все интерфейсы доступны с внешнего компьютера через SSH к 178.236.27.140:22. Прямой публичный HTTP по этому IP завершается таймаутом. Nginx работает, поэтому вероятная причина — правила ingress вне виртуальной машины. Скрипты HTTPS-публикации через Cloudflare включены в комплект, но на стенде не запускались.

## Что работает

- ResourceManager на team-38-nn; два NodeManager на team-38-00 и team-38-01, оба RUNNING.
- HDFS NameNode, два DataNode и SecondaryNameNode с настоящими checkpoint.
- MapReduce JobHistory Server, Timeline / Application History Server и Web Application Proxy на edge.
- Агрегация логов в HDFS; история и события завершённых заданий.
- Nginx: общий портал, отдельный корневой порт для каждого UI, замена внутренних адресов в ответах и межсервисных редиректах. Изменяющие методы gateway блокирует.
- Отдельный одноузловой вариант на edge: собственные данные, конфигурация и службы. После демонстрации остановлен; основной кластер оставлен работающим.

## Результаты интеграционных проверок

WordCount и Python Hadoop Streaming сравниваются с эталоном через diff. Проверка узлов требует точное число живых DataNode и RUNNING NodeManager. fsck требует HEALTHY, отсутствие недореплицированных блоков и нужное число фактических копий каждого тестового блока.

```text
hadoop  1
hello   2
yarn    1
```

Одноузловой вариант: 1 NodeManager, 1 DataNode, репликация 1.

Основной вариант: 2 NodeManager, 2 DataNode, репликация 2, потерянных и повреждённых блоков нет.

| YARN application ID | Задание | Результат |
| --- | --- | --- |
| `application_1791716023192_0001` | word count | SUCCEEDED |
| `application_1791716023192_0002` | streamjob4270044929088360167.jar | SUCCEEDED |
| `application_1791716023192_0003` | word count | SUCCEEDED |

## Как открыть веб-интерфейсы

С внешнего компьютера из распакованного комплекта:

```bash
bash scripts/access.sh /path/to/your/private_key
```

Оставить терминал открытым и открыть [http://127.0.0.1:18080/](http://127.0.0.1:18080/). На портале есть ссылки на все службы. ResourceManager: [localhost:18088/cluster](http://127.0.0.1:18088/cluster); JobHistory: [localhost:19880/jobhistory](http://127.0.0.1:19880/jobhistory); Timeline: [localhost:18188/applicationhistory/](http://127.0.0.1:18188/applicationhistory/).

Для независимой автоматической внешней проверки сначала закрыть access.sh, чтобы освободить порты:

```bash
python3 scripts/verify-access.py /path/to/your/private_key evidence/check.json
```

Проверка сама открывает канал, загружает страницы и API, проверяет завершённые задания в JobHistory и Timeline, проходит WebProxy и скачивает настоящий тестовый файл через перенаправление NameNode → DataNode. После проверки канал закрывается.

Фактические HTTP-проверки (31)

| Локальный порт | Путь / метод | HTTP |
| --- | --- | --- |
| 18080 | / | 200 |
| 18088 | / | 200 |
| 18042 | / | 200 |
| 18043 | / | 200 |
| 19880 | / | 200 |
| 18188 | / | 200 |
| 19099 | / | 200 |
| 19870 | / | 200 |
| 19864 | / | 200 |
| 19865 | / | 200 |
| 19868 | / | 200 |
| 18188 | / (redirect header) | 302 |
| 18088 | /ws/v1/cluster/nodes | 200 |
| 18088 | /ws/v1/cluster/apps | 200 |
| 19880 | /ws/v1/history/mapreduce/jobs | 200 |
| 18188 | /ws/v1/timeline | 200 |
| 18188 | /ws/v1/applicationhistory/about | 200 |
| 18188 | /ws/v1/applicationhistory/apps | 200 |
| 18042 | /ws/v1/node/info | 200 |
| 18043 | /ws/v1/node/info | 200 |
| 19870 | /jmx | 200 |
| 19864 | /jmx | 200 |
| 19865 | /jmx | 200 |
| 19868 | /jmx | 200 |
| 19099 | /proxy/application_1791716023192_0003/ | 200 |
| 19870 | /webhdfs/v1/user/team?op=LISTSTATUS&user.name=team | 200 |
| 19870 | /webhdfs/v1/user/team/yarn-check-20261011-105419/input/text.txt?op=OPEN&user.name=team | 200 |
| 18088 | POST | 403 |
| 18042 | POST | 403 |
| 19880 | POST | 403 |
| 19870 | POST | 403 |

## Файлы и запуск

[README.md](README.md) содержит топологию, объяснение всех конфигурационных файлов, последовательность установки, управление службами и диагностику. `scripts/deploy.sh` выполняет полный цикл на edge. `generated/` содержит конфигурации для каждого узла и отдельного одноузлового варианта. Приватных SSH-ключей в архиве нет.

Сохранённые подтверждения:

- [Одноузловой контрольный прогон](evidence/single-node-final.log)
- [WordCount, Streaming, отчёт HDFS и fsck основного кластера](evidence/multi-node-final.log)
- [Внешние HTTP/API-проверки и сведения о заданиях](evidence/external-access.json)
- [Состояние служб, память, checkpoint SecondaryNameNode](evidence/services.txt)
- [Получение агрегированных логов завершённого приложения](evidence/aggregated-logs.txt)
- [HTTP 200 настоящего Application Master во время задания](evidence/live-proxy.json)
- [Окончательная проверка фактических копий каждого блока](evidence/hdfs-final.log)
- [Результат проверки прямого внешнего HTTP](evidence/direct-ingress.json)
- [Проверка синтаксиса скриптов и XML](evidence/local-validation.md)

## Границы результата

Это учебный non-HA кластер без Kerberos. SecondaryNameNode выполняет checkpoint и не заменяет отказавший NameNode. У WebProxy нет собственного списка приложений: на корне gateway размещена поясняющая страница, а настоящий путь `/proxy/application_…/` проверен и для работающего Application Master, и для завершённого задания. Application Master существует во время задания; завершённые MapReduce-задания доступны в JobHistory.

## Официальные источники

[Apache Hadoop 3.5.0](https://hadoop.apache.org/docs/r3.5.0/) · [Cluster Setup](https://hadoop.apache.org/docs/r3.5.0/hadoop-project-dist/hadoop-common/ClusterSetup.html) · [Timeline Server](https://hadoop.apache.org/docs/r3.5.0/hadoop-yarn/hadoop-yarn-site/TimelineServer.html) · [Web Application Proxy](https://hadoop.apache.org/docs/r3.5.0/hadoop-yarn/hadoop-yarn-site/WebApplicationProxy.html) · [WebHDFS API](https://hadoop.apache.org/docs/r3.5.0/hadoop-project-dist/hadoop-hdfs/WebHDFS.html) · [Cloudflare Quick Tunnels](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/).

Журналы проверок находятся в каталоге evidence.

