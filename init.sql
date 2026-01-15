-- Таблица для записей транскрипций
CREATE TABLE IF NOT EXISTS transcription_records (
    id VARCHAR(255) PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    file_size INTEGER,
    duration FLOAT,
    language VARCHAR(10),
    status VARCHAR(20) DEFAULT 'started',
    error_message TEXT,
    text_length INTEGER,
    processing_time FLOAT,
    confidence_score FLOAT,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    transcription_id VARCHAR(255),
    file_uuid VARCHAR(255)
);

-- Таблица для метрик производительности
CREATE TABLE IF NOT EXISTS performance_metrics (
    id SERIAL PRIMARY KEY,
    file_uuid VARCHAR(255) NOT NULL,
    metric_name VARCHAR(50) NOT NULL,
    metric_value FLOAT NOT NULL,
    unit VARCHAR(20) DEFAULT 'seconds',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица для системных метрик
CREATE TABLE IF NOT EXISTS system_metrics (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metric_type VARCHAR(50) NOT NULL,
    metric_value FLOAT NOT NULL,
    service VARCHAR(50) DEFAULT 'transcription',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица для статистики слов
CREATE TABLE IF NOT EXISTS word_statistics (
    id SERIAL PRIMARY KEY,
    file_uuid VARCHAR(255) NOT NULL,
    word VARCHAR(100) NOT NULL,
    count INTEGER NOT NULL,
    language VARCHAR(10),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для производительности
CREATE INDEX IF NOT EXISTS idx_transcription_records_created_at ON transcription_records(created_at);
CREATE INDEX IF NOT EXISTS idx_transcription_records_status ON transcription_records(status);
CREATE INDEX IF NOT EXISTS idx_transcription_records_file_uuid ON transcription_records(file_uuid);
CREATE INDEX IF NOT EXISTS idx_performance_metrics_file_uuid ON performance_metrics(file_uuid);
CREATE INDEX IF NOT EXISTS idx_system_metrics_timestamp ON system_metrics(timestamp);
CREATE INDEX IF NOT EXISTS idx_system_metrics_metric_type ON system_metrics(metric_type);
CREATE INDEX IF NOT EXISTS idx_word_statistics_file_uuid ON word_statistics(file_uuid);

