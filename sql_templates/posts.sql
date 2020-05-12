CREATE TABLE `blogs`.`posts` (
  `domain` VARCHAR(64) NOT NULL,
  `url` VARCHAR(512) NOT NULL,
  `author` VARCHAR(100) NULL,
  `title` VARCHAR(512) NULL,
  `title_sentiment` DOUBLE NULL DEFAULT NULL,
  `title_toxicity` DOUBLE NULL DEFAULT NULL,
  `published_date` DATETIME NULL,
  `content` MEDIUMTEXT NOT NULL,
  `content_sentiment` DOUBLE NULL DEFAULT NULL,
  `content_toxicity` DOUBLE NULL DEFAULT NULL,
  `content_html` MEDIUMTEXT NULL,
  `language` VARCHAR(45) DEFAULT NULL, 
  `links` JSON NULL,
  `crawled_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP(),
  PRIMARY KEY (`url`),
  UNIQUE INDEX `url_UNIQUE` (`url` ASC) VISIBLE,
  INDEX `domains` (`domain` ASC) VISIBLE)
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8mb4
COLLATE = utf8mb4_unicode_ci;
