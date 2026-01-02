-- phpMyAdmin SQL Dump
-- version 4.9.5deb2
-- https://www.phpmyadmin.net/
--
-- Host: localhost:3306
-- Generation Time: Jan 02, 2026 at 07:46 PM
-- Server version: 8.0.42-0ubuntu0.20.04.1
-- PHP Version: 7.4.3-4ubuntu2.29

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET AUTOCOMMIT = 0;
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `db_mng_olt`
--

-- --------------------------------------------------------

--
-- Table structure for table `login`
--

CREATE TABLE `login` (
  `id` int NOT NULL,
  `username` varchar(50) NOT NULL,
  `password` varchar(255) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Dumping data for table `login`
--

INSERT INTO `login` (`id`, `username`, `password`) VALUES
(1, 'admin', '41e5653fc7aeb894026d6bb7b2db7f65902b454945fa8fd65a6327047b5277fb');

-- --------------------------------------------------------

--
-- Table structure for table `olt`
--

CREATE TABLE `olt` (
  `id` int NOT NULL,
  `hostname` varchar(100) NOT NULL,
  `ip` varchar(50) NOT NULL,
  `username` varchar(100) NOT NULL,
  `password` varchar(100) NOT NULL,
  `community_read` varchar(100) NOT NULL,
  `community_write` varchar(100) NOT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------

--
-- Table structure for table `olt_logs`
--

CREATE TABLE `olt_logs` (
  `id` int NOT NULL,
  `raw_log` text NOT NULL,
  `log_time` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `hostname` varchar(100) DEFAULT NULL,
  `mac_address` varchar(17) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------

--
-- Table structure for table `onu_log`
--

CREATE TABLE `onu_log` (
  `id` bigint NOT NULL,
  `olt_id` int NOT NULL,
  `olt_ip` varchar(64) NOT NULL,
  `olt_hostname` varchar(128) NOT NULL,
  `onu_id` int NOT NULL,
  `onu_name` varchar(128) DEFAULT NULL,
  `macaddr` varchar(32) NOT NULL,
  `port_id` int NOT NULL,
  `status` varchar(50) NOT NULL,
  `receive_power` decimal(6,2) DEFAULT NULL,
  `rtt` decimal(6,2) DEFAULT NULL,
  `auth_state` tinyint DEFAULT NULL,
  `vendor` varchar(100) DEFAULT NULL,
  `last_down_reason` varchar(255) DEFAULT NULL,
  `last_down_time` varchar(64) DEFAULT NULL,
  `register_time` varchar(64) DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------

--
-- Table structure for table `telegram_bot`
--

CREATE TABLE `telegram_bot` (
  `id` int NOT NULL,
  `token` varchar(255) NOT NULL,
  `aktif` tinyint(1) DEFAULT '0'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------

--
-- Table structure for table `telegram_chat`
--

CREATE TABLE `telegram_chat` (
  `id` int NOT NULL,
  `kategori` enum('mati','los','up') NOT NULL,
  `chat_id` varchar(50) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Indexes for dumped tables
--

--
-- Indexes for table `login`
--
ALTER TABLE `login`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `username` (`username`);

--
-- Indexes for table `olt`
--
ALTER TABLE `olt`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `olt_logs`
--
ALTER TABLE `olt_logs`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_log_time` (`log_time`),
  ADD KEY `idx_hostname` (`hostname`),
  ADD KEY `idx_mac` (`mac_address`);

--
-- Indexes for table `onu_log`
--
ALTER TABLE `onu_log`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_created_at` (`created_at`),
  ADD KEY `idx_macaddr` (`macaddr`),
  ADD KEY `idx_olt_created` (`olt_id`,`created_at`),
  ADD KEY `idx_rx_status` (`receive_power`,`created_at`),
  ADD KEY `idx_mac_created` (`macaddr`,`created_at`);

--
-- Indexes for table `telegram_bot`
--
ALTER TABLE `telegram_bot`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `telegram_chat`
--
ALTER TABLE `telegram_chat`
  ADD PRIMARY KEY (`id`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `login`
--
ALTER TABLE `login`
  MODIFY `id` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- AUTO_INCREMENT for table `olt`
--
ALTER TABLE `olt`
  MODIFY `id` int NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `olt_logs`
--
ALTER TABLE `olt_logs`
  MODIFY `id` int NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `onu_log`
--
ALTER TABLE `onu_log`
  MODIFY `id` bigint NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `telegram_bot`
--
ALTER TABLE `telegram_bot`
  MODIFY `id` int NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `telegram_chat`
--
ALTER TABLE `telegram_chat`
  MODIFY `id` int NOT NULL AUTO_INCREMENT;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
