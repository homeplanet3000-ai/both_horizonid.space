/*M!999999\- enable the sandbox mode */ 
-- MariaDB dump 10.19  Distrib 10.11.15-MariaDB, for debian-linux-gnu (x86_64)
--
-- Host: localhost    Database: marzban
-- ------------------------------------------------------
-- Server version	10.11.15-MariaDB-ubu2204

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `admin_usage_logs`
--

DROP TABLE IF EXISTS `admin_usage_logs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `admin_usage_logs` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `admin_id` int(11) DEFAULT NULL,
  `used_traffic_at_reset` bigint(20) NOT NULL,
  `reset_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `admin_id` (`admin_id`),
  CONSTRAINT `admin_usage_logs_ibfk_1` FOREIGN KEY (`admin_id`) REFERENCES `admins` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `admin_usage_logs`
--

LOCK TABLES `admin_usage_logs` WRITE;
/*!40000 ALTER TABLE `admin_usage_logs` DISABLE KEYS */;
/*!40000 ALTER TABLE `admin_usage_logs` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `admins`
--

DROP TABLE IF EXISTS `admins`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `admins` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `username` varchar(34) DEFAULT NULL,
  `hashed_password` varchar(128) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `is_sudo` tinyint(1) DEFAULT 0,
  `password_reset_at` datetime DEFAULT NULL,
  `telegram_id` bigint(20) DEFAULT NULL,
  `discord_webhook` varchar(1024) DEFAULT NULL,
  `users_usage` bigint(20) NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_admins_username` (`username`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `admins`
--

LOCK TABLES `admins` WRITE;
/*!40000 ALTER TABLE `admins` DISABLE KEYS */;
INSERT INTO `admins` VALUES
(6,'admin','$2b$12$clrffq9GwJXUPB5M6pbBQOXd7eQZIQgXRZYzNGON86WP.IAoRUDt6','2026-01-05 11:41:37',1,NULL,1375385135,NULL,15573432226);
/*!40000 ALTER TABLE `admins` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `alembic_version`
--

DROP TABLE IF EXISTS `alembic_version`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `alembic_version` (
  `version_num` varchar(32) NOT NULL,
  PRIMARY KEY (`version_num`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `alembic_version`
--

LOCK TABLES `alembic_version` WRITE;
/*!40000 ALTER TABLE `alembic_version` DISABLE KEYS */;
INSERT INTO `alembic_version` VALUES
('2b231de97dc3');
/*!40000 ALTER TABLE `alembic_version` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `exclude_inbounds_association`
--

DROP TABLE IF EXISTS `exclude_inbounds_association`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `exclude_inbounds_association` (
  `proxy_id` int(11) DEFAULT NULL,
  `inbound_tag` varchar(256) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
  KEY `proxy_id` (`proxy_id`),
  KEY `exclude_inbounds_association_ibfk_1` (`inbound_tag`),
  CONSTRAINT `exclude_inbounds_association_ibfk_1` FOREIGN KEY (`inbound_tag`) REFERENCES `inbounds` (`tag`),
  CONSTRAINT `exclude_inbounds_association_ibfk_2` FOREIGN KEY (`proxy_id`) REFERENCES `proxies` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `exclude_inbounds_association`
--

LOCK TABLES `exclude_inbounds_association` WRITE;
/*!40000 ALTER TABLE `exclude_inbounds_association` DISABLE KEYS */;
/*!40000 ALTER TABLE `exclude_inbounds_association` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `hosts`
--

DROP TABLE IF EXISTS `hosts`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `hosts` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `remark` varchar(256) NOT NULL,
  `address` varchar(256) NOT NULL,
  `port` int(11) DEFAULT NULL,
  `inbound_tag` varchar(256) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
  `sni` varchar(1000) DEFAULT NULL,
  `host` varchar(1000) DEFAULT NULL,
  `security` enum('inbound_default','none','tls') NOT NULL DEFAULT 'inbound_default',
  `alpn` enum('h3','h3,h2','h3,h2,http/1.1','none','h2','http/1.1','h2,http/1.1') NOT NULL,
  `fingerprint` enum('none','chrome','firefox','safari','ios','android','edge','360','qq','random','randomized') NOT NULL DEFAULT 'none',
  `allowinsecure` tinyint(1) DEFAULT NULL,
  `is_disabled` tinyint(1) DEFAULT NULL,
  `path` varchar(256) DEFAULT NULL,
  `mux_enable` tinyint(1) NOT NULL DEFAULT 0,
  `fragment_setting` varchar(100) DEFAULT NULL,
  `random_user_agent` tinyint(1) NOT NULL DEFAULT 0,
  `noise_setting` varchar(2000) DEFAULT NULL,
  `use_sni_as_host` tinyint(1) NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`),
  KEY `hosts_ibfk_1` (`inbound_tag`),
  CONSTRAINT `hosts_ibfk_1` FOREIGN KEY (`inbound_tag`) REFERENCES `inbounds` (`tag`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `hosts`
--

LOCK TABLES `hosts` WRITE;
/*!40000 ALTER TABLE `hosts` DISABLE KEYS */;
INSERT INTO `hosts` VALUES
(1,'🚀 Marz ({USERNAME}) [{PROTOCOL} - {TRANSPORT}]','{SERVER_IP}',NULL,'VLESS_REALITY',NULL,NULL,'inbound_default','none','none',NULL,0,NULL,0,NULL,0,NULL,0),
(2,'🚀 Marz ({USERNAME}) [{PROTOCOL} - {TRANSPORT}]','{SERVER_IP}',NULL,'VLESS_WS_CDN',NULL,NULL,'inbound_default','none','none',NULL,0,NULL,0,NULL,0,NULL,0);
/*!40000 ALTER TABLE `hosts` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `inbounds`
--

DROP TABLE IF EXISTS `inbounds`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `inbounds` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `tag` varchar(256) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_inbounds_tag` (`tag`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `inbounds`
--

LOCK TABLES `inbounds` WRITE;
/*!40000 ALTER TABLE `inbounds` DISABLE KEYS */;
INSERT INTO `inbounds` VALUES
(1,'VLESS_REALITY'),
(2,'VLESS_WS_CDN');
/*!40000 ALTER TABLE `inbounds` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `jwt`
--

DROP TABLE IF EXISTS `jwt`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `jwt` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `secret_key` varchar(64) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `jwt`
--

LOCK TABLES `jwt` WRITE;
/*!40000 ALTER TABLE `jwt` DISABLE KEYS */;
INSERT INTO `jwt` VALUES
(1,'5140deb5ebb393684ca6d4792977016063e018646afa0d9b5837bdbef2e54977');
/*!40000 ALTER TABLE `jwt` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `next_plans`
--

DROP TABLE IF EXISTS `next_plans`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `next_plans` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `data_limit` bigint(20) NOT NULL,
  `expire` int(11) DEFAULT NULL,
  `add_remaining_traffic` tinyint(1) NOT NULL DEFAULT 0,
  `fire_on_either` tinyint(1) NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `next_plans_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `next_plans`
--

LOCK TABLES `next_plans` WRITE;
/*!40000 ALTER TABLE `next_plans` DISABLE KEYS */;
/*!40000 ALTER TABLE `next_plans` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `node_usages`
--

DROP TABLE IF EXISTS `node_usages`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `node_usages` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `created_at` datetime NOT NULL,
  `node_id` int(11) DEFAULT NULL,
  `uplink` bigint(20) DEFAULT NULL,
  `downlink` bigint(20) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `created_at` (`created_at`,`node_id`),
  KEY `node_id` (`node_id`),
  CONSTRAINT `node_usages_ibfk_1` FOREIGN KEY (`node_id`) REFERENCES `nodes` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=23 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `node_usages`
--

LOCK TABLES `node_usages` WRITE;
/*!40000 ALTER TABLE `node_usages` DISABLE KEYS */;
INSERT INTO `node_usages` VALUES
(1,'2026-01-05 12:00:00',NULL,699394,964817),
(2,'2026-01-05 13:00:00',NULL,17575672,57548936),
(3,'2026-01-05 14:00:00',NULL,25600095,124562025),
(4,'2026-01-05 15:00:00',NULL,3790157,29697559),
(5,'2026-01-05 16:00:00',NULL,1851643,589301483),
(6,'2026-01-05 17:00:00',NULL,38419,21874121),
(7,'2026-01-06 12:00:00',NULL,3357350,30380111),
(8,'2026-01-06 13:00:00',NULL,5153630,2823639605),
(9,'2026-01-06 14:00:00',NULL,1187422,319803561),
(10,'2026-01-06 16:00:00',NULL,3504323,514149925),
(11,'2026-01-06 17:00:00',NULL,5245034,3091327696),
(12,'2026-01-06 19:00:00',NULL,7615819,70689116),
(13,'2026-01-07 00:00:00',NULL,8114639,4991295561),
(14,'2026-01-07 07:00:00',NULL,2243328,139075855),
(15,'2026-01-07 08:00:00',NULL,16329403,154301664),
(16,'2026-01-07 09:00:00',NULL,196,1612),
(17,'2026-01-07 14:00:00',NULL,3406729,158326229),
(18,'2026-01-07 15:00:00',NULL,3218414,91921283),
(19,'2026-01-07 16:00:00',NULL,7693007,673197191),
(20,'2026-01-07 17:00:00',NULL,12483525,1037081456),
(21,'2026-01-07 18:00:00',NULL,8371947,505465675),
(22,'2026-01-07 19:00:00',NULL,618608,4873363);
/*!40000 ALTER TABLE `node_usages` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `node_user_usages`
--

DROP TABLE IF EXISTS `node_user_usages`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `node_user_usages` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `created_at` datetime NOT NULL,
  `user_id` int(11) DEFAULT NULL,
  `node_id` int(11) DEFAULT NULL,
  `used_traffic` bigint(20) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `created_at` (`created_at`,`user_id`,`node_id`),
  KEY `node_id` (`node_id`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `node_user_usages_ibfk_1` FOREIGN KEY (`node_id`) REFERENCES `nodes` (`id`),
  CONSTRAINT `node_user_usages_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=27 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `node_user_usages`
--

LOCK TABLES `node_user_usages` WRITE;
/*!40000 ALTER TABLE `node_user_usages` DISABLE KEYS */;
INSERT INTO `node_user_usages` VALUES
(15,'2026-01-07 00:00:00',38,NULL,4999421492),
(16,'2026-01-07 07:00:00',38,NULL,141766419),
(17,'2026-01-07 08:00:00',38,NULL,170250071),
(18,'2026-01-07 09:00:00',38,NULL,1808),
(19,'2026-01-07 14:00:00',40,NULL,161766781),
(20,'2026-01-07 15:00:00',40,NULL,71045989),
(21,'2026-01-07 15:00:00',74,NULL,24151257),
(22,'2026-01-07 15:00:00',38,NULL,1810),
(23,'2026-01-07 16:00:00',40,NULL,683271246),
(24,'2026-01-07 17:00:00',40,NULL,1047763036),
(25,'2026-01-07 18:00:00',40,NULL,514045350),
(26,'2026-01-07 19:00:00',40,NULL,5504051);
/*!40000 ALTER TABLE `node_user_usages` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `nodes`
--

DROP TABLE IF EXISTS `nodes`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `nodes` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(256) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `address` varchar(256) NOT NULL,
  `port` int(11) NOT NULL,
  `api_port` int(11) NOT NULL,
  `status` enum('connected','connecting','error','disabled') NOT NULL,
  `last_status_change` datetime DEFAULT NULL,
  `message` varchar(1024) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `uplink` bigint(20) DEFAULT NULL,
  `downlink` bigint(20) DEFAULT NULL,
  `xray_version` varchar(32) DEFAULT NULL,
  `usage_coefficient` float NOT NULL DEFAULT 1,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `nodes`
--

LOCK TABLES `nodes` WRITE;
/*!40000 ALTER TABLE `nodes` DISABLE KEYS */;
/*!40000 ALTER TABLE `nodes` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `notification_reminders`
--

DROP TABLE IF EXISTS `notification_reminders`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `notification_reminders` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) DEFAULT NULL,
  `type` enum('expiration_date','data_usage') NOT NULL,
  `expires_at` datetime DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `threshold` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `notification_reminders_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `notification_reminders`
--

LOCK TABLES `notification_reminders` WRITE;
/*!40000 ALTER TABLE `notification_reminders` DISABLE KEYS */;
/*!40000 ALTER TABLE `notification_reminders` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `proxies`
--

DROP TABLE IF EXISTS `proxies`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `proxies` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) DEFAULT NULL,
  `type` enum('VMess','VLESS','Trojan','Shadowsocks') NOT NULL,
  `settings` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`settings`)),
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `proxies_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `proxies`
--

LOCK TABLES `proxies` WRITE;
/*!40000 ALTER TABLE `proxies` DISABLE KEYS */;
INSERT INTO `proxies` VALUES
(8,38,'VLESS','{\"id\": \"404de8a0-ff1e-4338-9ac0-b4b720ad6ae2\", \"flow\": \"xtls-rprx-vision\"}'),
(10,40,'VLESS','{\"id\": \"e481b895-ea07-4527-b734-c2bb2a306bf9\", \"flow\": \"\"}'),
(11,74,'VLESS','{\"id\": \"8832250f-ff82-40bf-86b2-7c1efa155816\", \"flow\": \"xtls-rprx-vision\"}'),
(12,80,'VLESS','{\"id\": \"ae729c6e-9530-49b3-b9c0-307acc9ec89b\", \"flow\": \"\"}');
/*!40000 ALTER TABLE `proxies` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `system`
--

DROP TABLE IF EXISTS `system`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `system` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `uplink` bigint(20) DEFAULT NULL,
  `downlink` bigint(20) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `system`
--

LOCK TABLES `system` WRITE;
/*!40000 ALTER TABLE `system` DISABLE KEYS */;
INSERT INTO `system` VALUES
(1,138098754,15429478844);
/*!40000 ALTER TABLE `system` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `template_inbounds_association`
--

DROP TABLE IF EXISTS `template_inbounds_association`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `template_inbounds_association` (
  `user_template_id` int(11) DEFAULT NULL,
  `inbound_tag` varchar(256) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
  KEY `user_template_id` (`user_template_id`),
  KEY `template_inbounds_association_ibfk_1` (`inbound_tag`),
  CONSTRAINT `template_inbounds_association_ibfk_1` FOREIGN KEY (`inbound_tag`) REFERENCES `inbounds` (`tag`),
  CONSTRAINT `template_inbounds_association_ibfk_2` FOREIGN KEY (`user_template_id`) REFERENCES `user_templates` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `template_inbounds_association`
--

LOCK TABLES `template_inbounds_association` WRITE;
/*!40000 ALTER TABLE `template_inbounds_association` DISABLE KEYS */;
/*!40000 ALTER TABLE `template_inbounds_association` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `tls`
--

DROP TABLE IF EXISTS `tls`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `tls` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `key` varchar(4096) NOT NULL,
  `certificate` varchar(2048) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `tls`
--

LOCK TABLES `tls` WRITE;
/*!40000 ALTER TABLE `tls` DISABLE KEYS */;
INSERT INTO `tls` VALUES
(1,'-----BEGIN PRIVATE KEY-----\nMIIJQwIBADANBgkqhkiG9w0BAQEFAASCCS0wggkpAgEAAoICAQDeMCUy1mJwVssK\n0jl9CAYNlaDfXKWI0n5zMYP/fhaRA3k27TqRNry8gl8sKXZ9pBHcbfrKU3lnPBj9\nMq/+5/NJaCuU+bzk0DF5Xoj90/1k2WJ3cxER9I3uZ7I3UfBnWZolYJtW0whw5xea\neEx11y+hUpe0R9Ddusm6PV6D8JWxjUepbjVs0mOz6wuy77smezYI4iPcJa87v5ab\nvK8K3J79cSwm3y46s/7uEZNBd902kSQEczhMJk2Ry3tmS0Nfw6JRh4u1UT9JQwPM\nev3LDnaANjPsxO/etVK+jl5sJOlQeezpV24TUJ/ShrnIdKvCHUQTlh05Prf08Png\nLsdXAp5V4BmSbmA6fnlVssQHPwZMu792nz8T1nmBugnq9EYlRBD1qJD+RwAiH4hR\nv6uUjPvLuA2AStVzGaJFY3YoZ8+ORbWrsvuzDOv/RwD+A2nLZLo/qDmO0mmHu7lL\nB58i+7RIRFEBIuf/NTKkElmpMw1dtA8R8YBAm8e2e+fUgGfaHWJqyLLU/0CT+HOd\nsXWAAL6Om1ef+vEvE7NlrCfSk1Gq9HuNO6+Kq38NLPL4gfqHzY8fI+7Y6jgMWrxw\nGyogZiadESEu9XGwnR5hWzAdl5D7ySzfjFrkkCSCWa2VGjjUsxx2r6XWVHJpKoT3\nFTlLFfiQJuWqfuYnvWh+QmNJSk15OwIDAQABAoICABFFIL8Q1tnwhRu0N2+2ffH0\nXWq/Isa9xcJiaOYlANAIuxU/3zuGS6lDYO5n0qP1asX9bm7nihoyG6cil3dyxABC\nrpCH0NzgKdhLNs6z+ZArLXInaX5Byf5r5PhT0CHYXxjkp25aPN+5tqX1D8xhC3y4\nlL4Yju2NJTzqpDwRKTGBz74lqNVqjQFhFam05JEbJpoOKcdkzngQbj5wrhJkD5+X\nel0TH97EOt56Uz3VeUZShcAqzIduurzIWjEbTINXC3jW1k8jn42sPdFZBf0QhLl2\nfRa8QADJi0LwgfpZ7CCrOXTxrManj6SngC1KlEckSzRSiLb4XwgU6vc365qhw3i4\nPOSUED1WKU5bN0NfUf7kiVki8I/n9hfFs3TAvq6SWn19EgN6eyo2zi7vyU/hV2Yw\ntX5sKNU+k7LRT2A9bMT9Tnw39DdfcpPmks9boIwSgn6oDNa/TJxSFvgcas50N7Fl\ntEHYDdab9N9NDTbXa0Ye711R6aDRZriGYOB/PXl0Rj/IvkyjZ3DzkaB3DuoORIQi\n+mVEVNuaIIqhPgByul8hM3keojsH77IzvuAoOJlWAEHwOKHamTTXOBThl4p1Sywz\natJupkTmwdW0536r0CeJOhNd6Jcj+es784oOSrMuWBLGNfEBfeu3iHbQjnA/tgDx\nceEcPOMWNqGzqSoo60QBAoIBAQDwOAzWI2UTjcBeS1LNDhNZ4s95H9swmUetMkRg\nmsnY9TnJy1zW1OjxEBVQGAgD8WfGfS5a59MgEyjkIMd3wuRYlPayrs9YpxKvKSCL\naPD9c2f4f01YrQThoQZw1newjOQ5XkVmeoqHDmWNdDngdkWMMMQ1cIfZuD9AswBV\nsnZvJUvfHJC53nfHrqF/X/QppIxZlQUrXFoGOfNS151+/jZvkYelRrpKwL9KtDCI\nmHUEpBhWm8fmXX9KBHTA7gMisT2PitFJn1gClnNuCL6ej0+JyG42n4RTnL9wybiQ\nGbbauDy32KChAUR0/IGnNNQQfyPdhqDt4kmcOoCrcEtz+fw7AoIBAQDsyNsUupoy\nZq67nULW0DXWcR+LwMysaLu4DOX9Ihgf+URI753LgB6l9OHG6EvGFix02KF1V8s5\nVfOJ+la+8x0BwkBJWXyyqd6QeGI4lgaTK9jdfDNlqqOvAvMbHCZET9C5jVdPfYEN\npwuqKOH5IVG82cSTAWmayLXLRJCeMkn2a425vWV0UU6YkVIyt+pCuDEewXyfB1Ei\nLB264I5LxDwngnrguCIvWzGrHIMRxOW53KgY4S808zRLEaHQafHNE2ac3/J0AM3y\nvfsOXMNq1+SqQSI75yVPEk3sEUq1Gh4YJw9WWI566Jbql+t6avHwJ0XrWkkVSXRw\nGC8gZ2RAy6cBAoIBAQDhTuETVF1waqr8hk+iTsptq2OHqw5uVcY5t4UUyvn5SYCr\nOdfZFBdsSvaCiheygxEfxbfdwcRvOClJV0lfleeRAh8lVvrZntLSgZOpzoMCZeUl\n2VkVjCqg6eRdn3rhmDRTbo1PYi5eIG21sEa8tpHivLa7nNF+ruZ866eruViGRQgV\nuvgvrW7RVoTZMImVKWYOe8w+cD9ryZzknaF2RD+Qg4IjzePbS0/gZIOFCuHuuW6u\nhSyIcDd8mBNeBZ/hQTaJVN2Z3R+yRaT8lq0bkTU7+UcOaq21sraItlsqpUOxf85L\nbZ6zhLnNtCxzRQSGeImONMDqfi0moGSg6BGNNPKTAoIBABPpQ/r3QhYw6kqei8tS\nkORqeNOgr9VjrT1p4EEsB8lQhbx4YdWF/Y3JDN9UE2Mh5DUjLliWvGEi6CrXIUpH\nWU4Xjp5cZw8DF9MgPGozu3POwRrG4e+PrNn/rn++Gz2tVIj16Lyneh2yyVlSvMXd\nVmlCCrSt7rp0XE0ug9a5tdyB6NYQpiJk3+4WckoPiyR3JrJGZPteeyUbfpiDX5Ph\neYl9AGY7Nayzx3ZzHFZ3LzY05vHIpdaXCPOzFN9YuVucYQmaD2JP2wGplh38EPbA\nFtt2RLGy20FN8b2DKrwV6SfwyOpi4gBV5LLveX6+1X9zXf7PhcvDdIYkknnwF88X\nEQECggEBANj2jfvQimxx8W+WjnZxC4NvVmwWJ7wXVJ2GdYXFuCNEV4+LEJOL9+qE\n/sXbCHyfX5jLwU8/sLCp/ORpY458bextCZEHKRwUcQrPvrEDx/1VO45fm+T2/R6f\nxoKp8nNxPbdrWBXZeClxZPLsKphzI9OJqEnCiaMCWRtAJBL0yG9ATFtaKlbfg7kE\nKi6Frpk80detZxZ0bAYHGxoykH+e1uNyYLiKXaDHiyyUNY+dbe/UxJBlFgIXvXED\n5CaIlYvYxGc5hojq0ik1aNy2h6N7v5lmMnQxNYLxwEUGbnaaW8ExkfzvxdThC+Yh\nGFMkWmQRBsFe2MASAdomEKNcJRHJD2M=\n-----END PRIVATE KEY-----\n','-----BEGIN CERTIFICATE-----\nMIIEnDCCAoQCAQAwDQYJKoZIhvcNAQENBQAwEzERMA8GA1UEAwwIR296YXJnYWgw\nIBcNMjYwMTA1MTA1ODI0WhgPMjEyNTEyMTIxMDU4MjRaMBMxETAPBgNVBAMMCEdv\nemFyZ2FoMIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEA3jAlMtZicFbL\nCtI5fQgGDZWg31yliNJ+czGD/34WkQN5Nu06kTa8vIJfLCl2faQR3G36ylN5ZzwY\n/TKv/ufzSWgrlPm85NAxeV6I/dP9ZNlid3MREfSN7meyN1HwZ1maJWCbVtMIcOcX\nmnhMddcvoVKXtEfQ3brJuj1eg/CVsY1HqW41bNJjs+sLsu+7Jns2COIj3CWvO7+W\nm7yvCtye/XEsJt8uOrP+7hGTQXfdNpEkBHM4TCZNkct7ZktDX8OiUYeLtVE/SUMD\nzHr9yw52gDYz7MTv3rVSvo5ebCTpUHns6VduE1Cf0oa5yHSrwh1EE5YdOT639PD5\n4C7HVwKeVeAZkm5gOn55VbLEBz8GTLu/dp8/E9Z5gboJ6vRGJUQQ9aiQ/kcAIh+I\nUb+rlIz7y7gNgErVcxmiRWN2KGfPjkW1q7L7swzr/0cA/gNpy2S6P6g5jtJph7u5\nSwefIvu0SERRASLn/zUypBJZqTMNXbQPEfGAQJvHtnvn1IBn2h1iasiy1P9Ak/hz\nnbF1gAC+jptXn/rxLxOzZawn0pNRqvR7jTuviqt/DSzy+IH6h82PHyPu2Oo4DFq8\ncBsqIGYmnREhLvVxsJ0eYVswHZeQ+8ks34xa5JAkglmtlRo41LMcdq+l1lRyaSqE\n9xU5SxX4kCblqn7mJ71ofkJjSUpNeTsCAwEAATANBgkqhkiG9w0BAQ0FAAOCAgEA\ne3h7O8qORGaeyKNpnVR5sdIPWt25ovqpwuT5wGKqEdWQcgNz8+TWtINozgvVeO5/\nDEJPqJRJ5++Z7dNsJEYeITFnGs5m9n0pILJsp+5auwEM53M/nz4nIdKNiJNgj1Tt\nKf0jDPy+K1J1nV35hWtU2tn94A9dvJUU6dLC97Cj7P0TYsp1yelKn59mKAC8qQ8M\nM0MoB/ttN90//KSaAoMFOxxUaQDIrXqW60F6VRH/Mt4TkT6b4dKo7aRe53TNwtrO\nFQxN8PNMy2exzhjzfipCFSYW6OrZGcsG5YEcOlR3J2Ga6fhxSOYv7ptSfp30WDy1\nA005Zka7ucs//KZA39s57GvaffWCvT8x/DD8Uo5M+4prBXdcqB5HbjpgmLSC9IJt\nJY7y/mLHpIbiSacUmDQEW3tHaf+UHbEz4AM5MD/6AwxRzk9aARNd14OPe78UxLW+\n7C2obu+EttpuQNvvpj/MC/uNEc8U3ljBLhtskmHu3+5jBwLfwfkBEtfDT/aBbGW8\ntbnGJfmBunxF4AJjevTBQDtA16u1qa5ygv89tneDhl/RLIHLp7L3neEt8WuJFT9s\nE/PMqYYWkczgFmAkvdnq7zYB8IvInK8yWHmUxGhO+gZBx5lUD2Kv3Y3w8cXlmqPk\nX5Bv5qZIbfzI6LqzGHscCI9gCWb1k9cyzLps7MTGalo=\n-----END CERTIFICATE-----\n');
/*!40000 ALTER TABLE `tls` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `user_templates`
--

DROP TABLE IF EXISTS `user_templates`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_templates` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(64) NOT NULL,
  `data_limit` bigint(20) DEFAULT NULL,
  `expire_duration` bigint(20) DEFAULT NULL,
  `username_prefix` varchar(20) DEFAULT NULL,
  `username_suffix` varchar(20) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `user_templates`
--

LOCK TABLES `user_templates` WRITE;
/*!40000 ALTER TABLE `user_templates` DISABLE KEYS */;
/*!40000 ALTER TABLE `user_templates` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `user_usage_logs`
--

DROP TABLE IF EXISTS `user_usage_logs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_usage_logs` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) DEFAULT NULL,
  `used_traffic_at_reset` bigint(20) NOT NULL,
  `reset_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `user_usage_logs_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `user_usage_logs`
--

LOCK TABLES `user_usage_logs` WRITE;
/*!40000 ALTER TABLE `user_usage_logs` DISABLE KEYS */;
INSERT INTO `user_usage_logs` VALUES
(1,74,0,'2026-01-07 15:03:31');
/*!40000 ALTER TABLE `user_usage_logs` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `users` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `username` varchar(34) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `status` enum('on_hold','active','limited','expired','disabled') NOT NULL,
  `used_traffic` bigint(20) DEFAULT NULL,
  `data_limit` bigint(20) DEFAULT NULL,
  `expire` int(11) DEFAULT NULL,
  `created_at` datetime DEFAULT current_timestamp(),
  `admin_id` int(11) DEFAULT NULL,
  `data_limit_reset_strategy` enum('no_reset','day','week','month','year') NOT NULL DEFAULT 'no_reset',
  `sub_revoked_at` datetime DEFAULT NULL,
  `note` varchar(500) DEFAULT NULL,
  `sub_updated_at` datetime DEFAULT NULL,
  `sub_last_user_agent` varchar(512) DEFAULT NULL,
  `online_at` datetime DEFAULT NULL,
  `edit_at` datetime DEFAULT NULL,
  `on_hold_timeout` datetime DEFAULT NULL,
  `on_hold_expire_duration` bigint(20) DEFAULT NULL,
  `auto_delete_in_days` int(11) DEFAULT NULL,
  `last_status_change` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_users_username` (`username`),
  KEY `fk_users_admin_id_admins` (`admin_id`),
  CONSTRAINT `fk_users_admin_id_admins` FOREIGN KEY (`admin_id`) REFERENCES `admins` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=83 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `users`
--

LOCK TABLES `users` WRITE;
/*!40000 ALTER TABLE `users` DISABLE KEYS */;
INSERT INTO `users` VALUES
(38,'admin','active',5311441600,NULL,NULL,'2026-01-07 00:06:03',6,'no_reset',NULL,'','2026-01-07 00:06:17','HiddifyNext/2.1.5 (android) like ClashMeta v2ray sing-box','2026-01-07 15:04:03',NULL,NULL,NULL,NULL,'2026-01-07 00:06:03'),
(40,'user_1375385135','active',2483396453,NULL,NULL,'2026-01-07 10:58:01',6,'no_reset',NULL,NULL,NULL,NULL,'2026-01-07 19:22:33','2026-01-07 14:39:39',NULL,NULL,NULL,'2026-01-07 10:58:01'),
(74,'user_5583965302','active',24151257,NULL,NULL,'2026-01-07 14:54:46',6,'no_reset',NULL,NULL,NULL,NULL,'2026-01-07 15:07:23','2026-01-07 15:12:50',NULL,NULL,NULL,'2026-01-07 14:54:46'),
(80,'user_887280296','active',0,NULL,NULL,'2026-01-07 15:12:07',6,'no_reset',NULL,NULL,NULL,NULL,NULL,'2026-01-07 15:12:10',NULL,NULL,NULL,'2026-01-07 15:12:07');
/*!40000 ALTER TABLE `users` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-01-07 19:22:48
