-- init.sql

CREATE TABLE IF NOT EXISTS submissions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    submission_datetime TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    submitter VARCHAR(255) NOT NULL,
    submission_name VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS inputs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    submission_id INT,
    x DECIMAL (10,2),
    y DECIMAL (10,2),
    FOREIGN KEY (submission_id) REFERENCES submissions(id)
);

CREATE TABLE IF NOT EXISTS outputs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    input_id INT,
    `sum` DECIMAL (10,2),
    FOREIGN KEY (input_id) REFERENCES inputs(id)
);

INSERT INTO submissions (submitter, submission_name) VALUES
    ('John Smith', 'example submission');

INSERT INTO inputs (submission_id, x, y) VALUES
    (1, 1, 1),
    (1, 1, 2),
    (1, 1, 3);

INSERT INTO outputs (input_id, sum) VALUES
    (1, 2),
    (2, 3),
    (3, 4);