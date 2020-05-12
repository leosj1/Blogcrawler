CREATE TABLE `blogs`.`comments` (
  `domain` VARCHAR(64) NOT NULL,
  `url` VARCHAR(512) NOT NULL,
  `comment_id` VARCHAR(255) NOT NULL,
  `username` VARCHAR(255) NULL DEFAULT NULL,
  `user_id` VARCHAR(255) NULL DEFAULT NULL,
  `comment` TEXT NOT NULL,
  `sentiment` DOUBLE NULL DEFAULT NULL,
  `toxicity` DOUBLE NULL DEFAULT NULL,
  `comment_original` TEXT NULL DEFAULT NULL,
  `language` VARCHAR(45) DEFAULT NULL, 
  `links` JSON NULL DEFAULT NULL,
  `upvotes` INT NULL DEFAULT NULL,
  `downvotes` INT NULL DEFAULT NULL,
  `published_date` DATETIME NULL DEFAULT NULL,
  `reply_count` INT NULL DEFAULT NULL,
  `reply_to` VARCHAR(255) NULL DEFAULT NULL,
  `crawled_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP(),
  UNIQUE INDEX `comment_id_UNIQUE` (`comment_id` ASC) VISIBLE,
  PRIMARY KEY (`comment_id`),
  INDEX `URL` (`url` ASC, `domain` ASC) VISIBLE)
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8mb4
COLLATE = utf8mb4_unicode_ci;
