-- init.sql

CREATE TABLE IF NOT EXISTS submissions (
    submission_id INT AUTO_INCREMENT PRIMARY KEY,
    submission_datetime TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    submitter VARCHAR(50) NOT NULL,
    submission_name VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS amplicons (
    amplicon_id INT PRIMARY KEY AUTO_INCREMENT,
    submission_id INT,
    amplicon_name VARCHAR(100) NOT NULL,
    DNA_sequence TEXT NOT NULL,
    FOREIGN KEY (submission_id) REFERENCES submissions(submission_id)
);

CREATE TABLE IF NOT EXISTS primers_all_options (
    primer_id INT PRIMARY KEY AUTO_INCREMENT,
    submission_id INT,
    amplicon_id INT,
    primer_name VARCHAR(255) NOT NULL,
    direction VARCHAR(50) NOT NULL,
    option_group_index INT,
    primer_sequence TEXT NOT NULL,
    gc_clamp INT,
    `length` INT,
    gc_percentage DECIMAL (10,2),
    melt_temperature DECIMAL (10,2),
    melt_temp_target_distance DECIMAL (10,2),
    gc_percentage_target_distance DECIMAL (10,2),
    melt_temperature_score DECIMAL (10,2),
    gc_percentage_score DECIMAL (10,2),
    total_score DECIMAL (10,2),
    option_group_rank INT,
    FOREIGN KEY (submission_id) REFERENCES submissions(submission_id),
    FOREIGN KEY (amplicon_id) REFERENCES amplicons(amplicon_id)
);

INSERT INTO submissions (submitter, submission_name) VALUES
    ('John Smith', 'example submission');

INSERT INTO amplicons (submission_id, amplicon_name, DNA_sequence) VALUES
    (1,'example gene', 'AAATTTGGGCCCAAATTTGGGCCC');

INSERT INTO primers_all_options (
    submission_id,
    amplicon_id,
    primer_name,
    direction,
    option_group_index,
    primer_sequence,
    gc_clamp,
    `length`,
    gc_percentage,
    melt_temperature,
    melt_temp_target_distance,
    gc_percentage_target_distance,
    melt_temperature_score,
    gc_percentage_score,
    total_score,
    option_group_rank
) VALUES
    (1, 
     1, 
     "example_primer forward",
     "forward",
     1,
     "AAAT",
     0,
     4,
     0.0,
     52.0,
     10.0,
     50.0,
     0.5,
     0.3,
     0.8,
     1
    );