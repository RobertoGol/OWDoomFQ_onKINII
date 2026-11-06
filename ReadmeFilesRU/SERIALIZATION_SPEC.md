# Соглашения о данных и аудит размеров структур

Статус: **проектные схемы, не утверждённый wire protocol**. В текущем KINII нет подтверждённых типов `f32`, `i32`, `char[N]`; блоки `void` в старых документах следует читать как нейтральную C-подобную псевдозапись. Они не обязаны компилироваться `kinic`.

## 1. Общие правила

1. Разделять доменную модель, native C/C++ layout и сериализованный формат. Наличие `struct` не задаёт переносимый сетевой протокол.
2. Для wire-формата явно определить byte order, версию, длину, обязательные поля, лимиты массивов и поведение при неизвестной версии. Предлагаемый baseline — little-endian, явные поля без неявного padding.
3. Не сериализовать `ptr`, `custom_data_ptr`, `media_blob_ptr` как адреса процесса. Использовать persistent ID или offset внутри ограниченного blob.
4. Persistent UUID — 64 бита. Если сеть использует короткий ID, нужна таблица соответствия; нельзя молча обрезать UUID до `u32` (D-010).
5. Строки — ограниченные UTF-8 byte arrays либо length-prefixed строки. `char c` хранит один байт, а не строку.
6. Динамические массивы требуют count и bounds-check; пакет с ними не имеет заранее фиксированного размера.
7. CRC32 проверяет случайную порчу, но не аутентичность. Для защиты от подмены нужны серверная проверка и криптографическая аутентификация.
8. AEAD-пакет должен содержать или однозначно выводить nonce, ciphertext и tag. Один `encryption_flag` и IV без tag не доказывают E2EE.
9. Координаты chunk хранятся знаковым типом; float-поля требуют IEEE-754 binary32 и проверки NaN/Infinity при валидации.
10. Размеры ниже пересчитаны **после восстановления массивов, явно указанных комментариями**. Это аудит черновиков, а не обещание обратной совместимости с уже существующими сохранениями.

## 2. Как считались размеры

- `u8`/`char`: 1 байт; `u16`: 2; `u32`/`f32`: 4; `u64`: 8.
- **Packed payload**: сумма размеров полей, без padding, без внешнего заголовка версии/длины и без данных переменной длины.
- **Native x64**: естественное выравнивание скаляров, максимум 8 байт; массив наследует выравнивание элемента; trailing padding до выравнивания структуры. Предполагается обычный C/C++ ABI с 8-байтным `u64`, не упаковка компилятора.
- Это не расчет layout KINII и не гарантия одинакового `sizeof` на всех компиляторах. Перед реализацией нужны `static_assert` для native-структур и отдельные encode/decode tests для wire-формата.

## 3. Аудит фиксированных черновиков

<!-- schema-size-table:start -->
| Схема | Packed payload, байт | Native x64, байт | Было заявлено | Документ |
|---|---:|---:|---:|---|
| SurvivorNPCNode | 69 | 80 | 80 | AI_FACTION_SPEC.md |
| RaidBossController | 48 | 48 | 64 | AI_FACTION_SPEC.md |
| ColossusWalkerController | 115 | 120 | 96 | AI_FACTION_SPEC.md |
| PlayerProfile | 41 | 48 | 64 | CLAN_SPEC.md |
| ClanNode | 86 | 96 | 128 | CLAN_SPEC.md |
| PowerArmorFrame | 70 | 72 | 80 | COMBAT_EXO_SPEC.md |
| HiddenSafetyNode | 39 | 40 | 96 | COMBAT_EXO_SPEC.md |
| BaseEngineeringGrid | 37 | 40 | 128 | BASE_ENGINEERING_SPEC.md |
| GridNodeAppliance | 18 | 20 | 48 | BASE_ENGINEERING_SPEC.md |
| EnvironmentState | 30 | 36 | 64 | ENVIRONMENT_SPEC.md |
| InventoryItem | 28 | 32 | 32 | INVENTORY_SPEC.md |
| EntityTelemetry | 14 | 20 | 16 | MAP_SPEC.md |
| GlobalEvent | 53 | 56 | 64 | MAP_SPEC.md |
| NetPacketHeader | 18 | 20 | 20 | MULTIPLAYER_SPEC.md |
| QuestState | 33 | 40 | 64 | QUEST_RAID_SPEC.md |
| PlayerBountyContract | 29 | 40 | 96 | QUEST_RAID_SPEC.md |
| ServerInfo | 83 | 84 | 96 | SERVER_BROWSER_SPEC.md |
| SocialPostNode | 57 | 72 | 128 | SOCIAL_MESSENGER_SPEC.md |
| SurvivorBioState | 60 | 60 | 48 | SURVIVAL_SPEC.md |
| VehicleEntityState | 109 | 112 | 112 | VEHICLE_SPEC.md |
| WeaponModularGraph | 54 | 56 | 64 | WEAPON_CRAFT_SPEC.md |
| EmperorTitanState | 157 | 160 | 160 | EMPEROR_TITAN_SPEC.md |
| NetVoiceFramePacket | 114 | 116 | не указано | AUDIO_COMMS_SPEC.md |
<!-- schema-size-table:end -->

Машинно-читаемые поля и размеры находятся в [tools/docs_schemas.json](../tools/docs_schemas.json). Проверка: `python3 tools/check_docs.py`.

## 4. Исправления очевидных ошибок записи

- `world_pos_xyz`, `core_pos_xyz`, `velocity_vec`, `wind_vector_xyz` → массивы `[3]`, если комментарий описывает три координаты.
- Шесть опор Титана → `leg_foot_world_xyz[6][3]`; шесть ног Колосса → массив 18 координат или явно описанный массив узлов, а не один `f32`.
- `target_chunk_xy`, `location_chunk_xy`, `current_chunk_xy` → два элемента, а не один скаляр.
- `event_title` → ограниченный byte array `[32]` с правилом terminator/длины; не одиночный `char`.
- `aes_iv` / `iv` для AES-GCM → `[12]` байт в предлагаемом профиле; tag хранится отдельно или appended по явному правилу.
- `encrypted_data` / `encrypted_payload` → переменной длины blob, не одиночный символ.
- Старый `EmperorTitanState` с неопределённым списком игроков удалён как дубликат; используется одна схема `EmperorTitanState` с числом игроков и внешним session registry. Вместимость остаётся D-003.

## 5. Переменные пакеты

Следующие структуры нельзя объявлять фиксированными до определения envelope:

- `ChunkDeltaPacket`: массивы изменений линий и построенных объектов; SHA-256 требует 32 байта, либо нужен отдельный явно названный укороченный не cryptographic ID.
- `MobileChatPacket`, `MessengerEnvelope`: ciphertext, вложения, nonce/tag и длина.
- `NetPlayerUpdatePacket`: зависит от финального заголовка, ID и маски команд.
- Сообщения с медиа/текстом: pointer заменяется ID/blob reference; размер считается по фактической длине.

## 6. Что ещё нужно утвердить

Версия протокола, порядок байтов, signedness координат, квантование, строковый terminator, максимумы пакетов, совместимость сохранений, endian-safe encode/decode, шифрование и границы аутентификации. До этого числа в таблице служат для исправления документации, а не для отправки пакетов по сети.

