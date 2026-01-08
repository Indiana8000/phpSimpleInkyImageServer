<?php
$input  = json_decode(file_get_contents('php://input'), true);
$action = $_GET['action'] ?? '';

// Initiate Configuration Array and read config.php
$GLOBALS['CONFIG'] = Array();
require_once('config.php');

// Connect to Database
try {
	if($GLOBALS['CONFIG']['DB_TYPE'] == 'sqlite') {
        // Define Functions
        $GLOBALS['CONFIG']['DB_X_RANDOM'] = 'RANDOM()';
        $GLOBALS['CONFIG']['DB_X_NOW']    = "DATETIME('now')";
        // Connect
        $GLOBALS['DB'] = new PDO($GLOBALS['CONFIG']['DB_DSN']);
	} else if($GLOBALS['CONFIG']['DB_TYPE'] == 'mysql') {
        // Define Functions
        $GLOBALS['CONFIG']['DB_X_RANDOM'] = 'RAND()';
        $GLOBALS['CONFIG']['DB_X_NOW']    = "NOW()";
        // Connect
        $GLOBALS['DB'] = new PDO($GLOBALS['CONFIG']['DB_DSN'], $GLOBALS['CONFIG']['DB_USER'], $GLOBALS['CONFIG']['DB_PASSWD'], Array(PDO::MYSQL_ATTR_FOUND_ROWS => true, PDO::ATTR_EMULATE_PREPARES => true));
		$GLOBALS['DB']->exec("SET NAMES 'utf8'");
	} else {
		die('Unknown Connection Type!');
	}
} catch(PDOException $e) {
	die('Connection failed: ' . $e->getMessage());
}

// Create Tables if missing
try {
	$stmt = $GLOBALS['DB']->query("SELECT * FROM inky_settings");
} catch(PDOException $e) {
	if($GLOBALS['CONFIG']['DB_TYPE'] == 'sqlite') {
		$GLOBALS['DB']->exec("CREATE TABLE inky_settings (s_key TEXT, s_value TEXT)");
		$GLOBALS['DB']->exec("CREATE TABLE inky_images   (imagename TEXT, views NUMBER, likeit NUMBER, lastupdate NUMBER)");
		$GLOBALS['DB']->exec("CREATE TABLE inky_history  (imagename TEXT, viewed TEXT)");
	} else if($GLOBALS['CONFIG']['DB_TYPE'] == 'mysql') {
        $DB_ENGINE = 'ENGINE=Aria DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci PAGE_CHECKSUM=1';
		$GLOBALS['DB']->exec("CREATE TABLE inky_settings (s_key varchar(250), s_value varchar(250)) " . $DB_ENGINE);
		$GLOBALS['DB']->exec("CREATE TABLE inky_images   (imagename varchar(250), views int(11), likeit int(11), lastupdate int(1)) " . $DB_ENGINE);
		$GLOBALS['DB']->exec("CREATE TABLE inky_history  (imagename varchar(250), viewed datetime) " . $DB_ENGINE);
	}
}

// Process Call
switch($action) {
    case 'inky':
        break;
    case 'webGetImageList':
        $data = [];
        $stmt = $GLOBALS['DB']->query("SELECT ih.imagename, ii.views, ii.likeit, ih.viewed FROM inky_history ih JOIN inky_images ii ON ii.imagename = ih.imagename ORDER BY ih.viewed DESC LIMIT 9");
        $data['lastViewed'] = $stmt->fetchAll(PDO::FETCH_ASSOC);
        $stmt = $GLOBALS['DB']->query("SELECT ii.imagename, ii.views, ii.likeit, MAX(ih.viewed) as viewed FROM inky_images ii LEFT JOIN inky_history ih ON ii.imagename = ih.imagename WHERE ii.likeit <> 0 GROUP BY ii.imagename, ii.views, ii.likeit ORDER BY ii.likeit DESC, ii.imagename ASC");
        $data['liked'] = $stmt->fetchAll(PDO::FETCH_ASSOC);
        header('Content-Type: application/json');
        echo json_encode($data);
        break;
    case 'webGetRandomImage':
        $stmt = $GLOBALS['DB']->query("SELECT * FROM inky_images WHERE likeit >= 0 ORDER BY (1 / POW(views + 1, 1.3)) * (RAND() + 0.0001) DESC LIMIT 1");
        $data = $stmt->fetch(PDO::FETCH_ASSOC);
        header('Content-Type: application/json');
        echo json_encode($data);
        break;
    case 'webGetRandomImageRaw':
        $stmt = $GLOBALS['DB']->query("SELECT * FROM inky_images WHERE likeit >= 0 ORDER BY (1 / POW(views + 1, 1.3)) * (RAND() + 0.0001) DESC LIMIT 1");
        $data = $stmt->fetch(PDO::FETCH_ASSOC);
        $file = $data['imagename'];
        $imageType = exif_imagetype($file);
        $mime = $imageType ? image_type_to_mime_type($imageType) : 'text/text';
        header('Content-Type: ' . $mime);
        header('Content-Length: ' . filesize($file));
        readfile($file);           
        break;
    case 'webUpdateDatabase':
        $result = updateDatabase();
        header('Content-Type: application/json');
        echo json_encode($result);
        break;
    case 'webSendToInky':
        $url = $GLOBALS['CONFIG']['INKY_URL'] . '/?action=' . $input['action'];
        if(isset($input['url'])) {
            // TBD: If URL starts with HTTP download image to temp file and display
            if(file_exists($input['url']))
                $url .= '&url=' . urlencode($input['url']);
            else
                die("File not found!");
        }
        $content = file_get_contents($url);
        //header('Content-Type: application/json');
        echo $content;
        //echo json_encode($result);
        break;


    default: http_response_code(400); echo 'Unknown action';
}



function updateDatabase() {
    $result = ['new' => [], 'deleted' => []];

    // Get lowest View Count
    $stmt = $GLOBALS['DB']->query("SELECT min(views) as min_views FROM inky_images WHERE views > 0");
    $row = $stmt->fetch(PDO::FETCH_ASSOC);
    $min_views = $row['min_views'];
    if(!$min_views) $min_views = 0;

    // Mark all images as deleted
    $GLOBALS['DB']->exec("UPDATE inky_images SET lastupdate = 0");

    // Read Directory
    $files = glob($GLOBALS['CONFIG']['IMAGE_PATH'], \GLOB_BRACE);
    for($i = 0;$i < count($files);$i++) {
        $stmt = $GLOBALS['DB']->prepare("UPDATE inky_images SET lastupdate = 1 WHERE imagename = :imagename");
        $stmt->bindValue(':imagename', $files[$i], PDO::PARAM_STR);
        $stmt->execute();
        if($stmt->rowCount() == 0) {
            $stmt = $GLOBALS['DB']->prepare("INSERT INTO inky_images (imagename, views, lastupdate, likeit) VALUES (:imagename, :views, 1, 0)");
            $stmt->bindValue(':imagename', $files[$i], PDO::PARAM_STR);
            $stmt->bindValue(':views'    , $min_views, PDO::PARAM_INT);
            $stmt->execute();
            array_push($result['new'], $files[$i]);
        }
    }

    // Deleted Images
    $stmt = $GLOBALS['DB']->query("SELECT imagename FROM inky_images WHERE lastupdate = 0");
    $result['deleted'] = $stmt->fetchAll(PDO::FETCH_ASSOC);
    $stmt = $GLOBALS['DB']->query("DELETE FROM inky_images WHERE lastupdate = 0");

    return $result;
}

?>