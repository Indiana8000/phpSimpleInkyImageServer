<?php
// Initiate Configuration Array
$GLOBALS['CONFIG'] = Array();

// URL to your RPI running run.py
$GLOBALS['CONFIG']['INKY_URL']    = 'http://192.168.1.2:8080';

// Database Connection SQLite
$GLOBALS['CONFIG']['DB_TYPE']     = 'sqlite';
$GLOBALS['CONFIG']['DB_DSN']      = 'sqlite:inky.sqlite';
$GLOBALS['CONFIG']['DB_X_RANDOM'] = 'RANDOM()';
$GLOBALS['CONFIG']['DB_X_NOW']    = "DATETIME('now')";


// Database Connection MySQL
/*
$GLOBALS['CONFIG']['DB_TYPE']     = 'mysql';
$GLOBALS['CONFIG']['DB_DSN']      = 'mysql:host=127.0.0.1;dbname=inky';
$GLOBALS['CONFIG']['DB_USER']     = 'inky';
$GLOBALS['CONFIG']['DB_PASSWD']   = 'inky';
$GLOBALS['CONFIG']['DB_X_RANDOM'] = 'RAND()';
$GLOBALS['CONFIG']['DB_X_NOW']    = "NOW()";
*/

// Timezone / Language
date_default_timezone_set('Europe/Berlin');
setlocale(LC_TIME, 'de_DE@euro', 'de_DE', 'de', 'de');

// Connect
try {
	if($GLOBALS['CONFIG']['DB_TYPE'] == 'sqlite') {
		$GLOBALS['DB'] = new PDO($GLOBALS['CONFIG']['DB_DSN']);
	} else if($GLOBALS['CONFIG']['DB_TYPE'] == 'mysql') {
		$GLOBALS['DB'] = new PDO($GLOBALS['CONFIG']['DB_DSN'], $GLOBALS['CONFIG']['DB_USER'], $GLOBALS['CONFIG']['DB_PASSWD'], Array(PDO::MYSQL_ATTR_FOUND_ROWS => true, PDO::ATTR_EMULATE_PREPARES => true));
		$GLOBALS['DB']->exec("SET NAMES 'utf8'");
	} else {
		die('Unknown Connection Type!');
	}
} catch(PDOException $e) {
	die('Connection failed: ' . $e->getMessage());
}

// Create DB
try {
	$stmt = $GLOBALS['DB']->query("SELECT * FROM inky_settings");
} catch(PDOException $e) {
	if($GLOBALS['CONFIG']['DB_TYPE'] == 'sqlite') {
		$GLOBALS['DB']->exec("CREATE TABLE inky_settings (s_key TEXT, s_value TEXT)");
		$GLOBALS['DB']->exec("CREATE TABLE inky_images   (imagename TEXT, views NUMBER, likeit NUMBER, lastupdate NUMBER)");
		$GLOBALS['DB']->exec("CREATE TABLE inky_history  (imagename TEXT, viewed TEXT)");
	} else if($GLOBALS['CONFIG']['DB_TYPE'] == 'mysql') {
		$GLOBALS['DB']->exec("CREATE TABLE inky_settings (s_key varchar(250), s_value varchar(250)) ENGINE=Aria DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci PAGE_CHECKSUM=1");
		$GLOBALS['DB']->exec("CREATE TABLE inky_images   (imagename varchar(250), views int(11), likeit int(11), lastupdate int(1)) ENGINE=Aria DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci PAGE_CHECKSUM=1");
		$GLOBALS['DB']->exec("CREATE TABLE inky_history  (imagename varchar(250), viewed datetime) ENGINE=Aria DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci PAGE_CHECKSUM=1");
	}
}

// Process Call
if(isset($_REQUEST['inky'])) { // Called by inky.py
	if(isset($_REQUEST['likeit'])) { // Like it +/- button pressed
		$likeit = 1; if(intval($_REQUEST['likeit']) < 0) $likeit = -1;
		// Get Last Image
        if(isset($_REQUEST['image'])) {
            $imagename = $_REQUEST['image'];
        } else {
            $stmt = $GLOBALS['DB']->query("SELECT imagename FROM inky_history ORDER BY viewed DESC LIMIT 1");
            $row = $stmt->fetch(PDO::FETCH_ASSOC);
            $imagename = $row["imagename"];
        }
		// Update favorit counter
		$stmt = $GLOBALS['DB']->prepare("UPDATE inky_images SET likeit = likeit + :likeit WHERE imagename = :imagename");
		$stmt->bindValue(':likeit'   , $likeit   , PDO::PARAM_INT);
		$stmt->bindValue(':imagename', $imagename, PDO::PARAM_STR);
		$stmt->execute();
		echo $imagename;
	} else { // Any other button pressed
		// Get pressed Button
		$button = 0; if(isset($_REQUEST['button'])) $button = intval($_REQUEST['button']);
        // TBD: 
        // Use $_REQUEST['resx'] and $_REQUEST['resy'] for different sources
		if($button == 6) { // Get random image from favorit list
			$stmt = $GLOBALS['DB']->query("SELECT imagename FROM inky_images WHERE lastupdate > 0 AND likeit > 0 ORDER BY ".$GLOBALS['CONFIG']['DB_X_RANDOM']." LIMIT 1");
		} else { // Get any random image
			$stmt = $GLOBALS['DB']->query("SELECT max(views) - min(views) + 1 as views_count FROM inky_images WHERE lastupdate > 0 AND likeit > -2");
			$row = $stmt->fetch(PDO::FETCH_ASSOC);
			$stmt = $GLOBALS['DB']->query("SELECT imagename FROM inky_images WHERE lastupdate > 0 AND likeit > -2 ORDER BY views + FLOOR(".$GLOBALS['CONFIG']['DB_X_RANDOM']." * ".$row['views_count']."), ".$GLOBALS['CONFIG']['DB_X_RANDOM']." LIMIT 1");
		}
		$row = $stmt->fetch(PDO::FETCH_ASSOC);
		$imagename = $row["imagename"];

		if($button == 1 || $button == 2 || $button == 5) { // Update view counter
			$stmt = $GLOBALS['DB']->prepare("UPDATE inky_images SET views = views + 1 WHERE imagename = :imagename");
			$stmt->bindValue(':imagename', $imagename, PDO::PARAM_STR);
			$stmt->execute();
		}

		// Write History
		$stmt = $GLOBALS['DB']->prepare("INSERT INTO inky_history (viewed, imagename) VALUES (".$GLOBALS['CONFIG']['DB_X_NOW'].", :imagename)");
		$stmt->bindValue(':imagename', $imagename, PDO::PARAM_STR);
		$stmt->execute();

		// Output Image Name (Binary will be loaded directly with extra call)
        echo $imagename;
	}
} else {
	// Called by Browser
	if(isset($_REQUEST['update'])) { // Scan FS for new images
		echo '<html><head><title>phpSimpleInkyImageServer</title></head><body style="font-family: Tahoma;">';
		echo '<a href="?"><button>Back</button></a>';
		// Get lowest View Count
		$stmt = $GLOBALS['DB']->query("SELECT min(views) as min_views FROM inky_images WHERE views > 0");
		$row = $stmt->fetch(PDO::FETCH_ASSOC);
		$min_views = $row['min_views'];
		if(!$min_views) $min_views = 0;
		// Mark all images as deleted
		$GLOBALS['DB']->exec("UPDATE inky_images SET lastupdate = 0");
		// Read Directory
		echo "<table>";
		$files = glob("./images/*.png");
		for($i = 0;$i < count($files);$i++) {
			$stmt = $GLOBALS['DB']->prepare("UPDATE inky_images SET lastupdate = 1 WHERE imagename = :imagename");
			$stmt->bindValue(':imagename', $files[$i], PDO::PARAM_STR);
			$stmt->execute();
			if($stmt->rowCount() == 0) {
				$stmt = $GLOBALS['DB']->prepare("INSERT INTO inky_images (imagename, views, lastupdate, likeit) VALUES (:imagename, :views, 1, 0)");
				$stmt->bindValue(':imagename', $files[$i], PDO::PARAM_STR);
				$stmt->bindValue(':views'    , $min_views, PDO::PARAM_INT);
				$stmt->execute();
				echo "<tr style='background-color:yellow;'><td>" . $files[$i] . "</td><td>NEW</td>";
			} else {
				echo "<tr><td>" . $files[$i] . "</td><td>-</td>";
			}
			echo "</tr>";
		}
		echo "</table>";
		echo '</body></html>';
	} else if(isset($_REQUEST['single'])) { // Show random image
		// Get random inage
		$stmt = $GLOBALS['DB']->query("SELECT max(views) - min(views) + 1 as views_count FROM inky_images WHERE lastupdate > 0");
		$row = $stmt->fetch(PDO::FETCH_ASSOC);
		$stmt = $GLOBALS['DB']->query("SELECT imagename FROM inky_images WHERE lastupdate > 0 ORDER BY views + FLOOR(".$GLOBALS['CONFIG']['DB_X_RANDOM']." * ".$row['views_count']."), ".$GLOBALS['CONFIG']['DB_X_RANDOM']." LIMIT 1");
		$row = $stmt->fetch(PDO::FETCH_ASSOC);
		$imagename = $row["imagename"];

		// Output
		echo '<html><head><title>phpSimpleInkyImageServer</title></head><body style="font-family: Tahoma;">';
		echo '<a href="?"><button>Back</button></a>';
		echo '<a style="text-decoration: none;" target="_blank" href="' . $GLOBALS['CONFIG']['INKY_URL'] . '/show/' . $imagename . '"><button>Show</button></a>';
		echo '<br/><br/>';
		echo '<img src="'.$imagename.'" />';
		echo '</body></html>';
	} else {
		// Show list of images
		echo '<html><head><title>phpSimpleInkyImageServer</title></head><body style="font-family: Tahoma;">';
		echo 'Browser: ';
		echo '<a href="?update=1"><button>Update Database</button></a>&nbsp;';
		echo '<a href="?single=1"><button>Display single image</button></a>&nbsp;';
		echo 'Inky: ';
		echo '<a href="' . $GLOBALS['CONFIG']['INKY_URL'] . '/next/" target="_blank"><button>Next image</button></a>&nbsp;';
		echo '<a href="' . $GLOBALS['CONFIG']['INKY_URL'] . '/clear/" target="_blank"><button>Clear screen</button></a>&nbsp;';
		echo '<br/><br/>';

		$i = 0;
		echo '<table style="border: 1px solid black; border-collapse: collapse; background-color: #333;">';
		echo '<tr><th colspan="3" style="font-size: 2em; background-color: #BBB; border-bottom: 1px solid black;">Last Viewed</th></tr>';
		echo '<tr>';
		$stmt = $GLOBALS['DB']->query("SELECT ih.imagename, ii.views, ii.likeit, ih.viewed FROM inky_history ih JOIN inky_images ii ON ii.imagename = ih.imagename ORDER BY ih.viewed DESC LIMIT 9");
		while($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
			if($i > 0 & $i++ % 3 == 0) echo "</tr><tr>";
			echo '<td style=""><div style="position: relative;"><img src="'.$row['imagename'].'" /><div style="position: absolute; bottom: 0px; left: 0px; width: 100%; color:white; text-align: center; white-space: nowrap; overflow: hidden; background-color: #4449;">'.$row['viewed'].' / Views: '.$row['views'].' / Likes: '.$row['likeit'].'<br/>'.basename($row['imagename']).'</div><div style="position: absolute; bottom: 0px; right: 5px; white-space: nowrap; overflow: hidden;"><a style="text-decoration: none;" target="_blank" href="' . $GLOBALS['CONFIG']['INKY_URL'] . '/show/' . $row['imagename'] . '">Show</a><br>&nbsp;</div></div></td>';
		}
		echo '</tr></table>';

		echo '<br/><br/>';

		$i = 0; $l;
		echo '<table style="border: 1px solid black; border-collapse: collapse; background-color: #333;">';
		echo '<tr><th colspan="3" style="font-size: 2em; background-color: #DDD; border-bottom: 1px solid black;">Favorits</th></tr>';
		echo '<tr>';
		$stmt = $GLOBALS['DB']->query("SELECT ii.imagename, ii.views, ii.likeit, MAX(ih.viewed) as viewed FROM inky_images ii LEFT JOIN inky_history ih ON ii.imagename = ih.imagename WHERE ii.likeit <> 0 GROUP BY ii.imagename, ii.views, ii.likeit ORDER BY ii.likeit DESC, ii.imagename ASC");
		while($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
			if(!isset($l)) {
				$l = $row['likeit'];
				echo '<th colspan="3" style="background-color: #BBB;">' . str_repeat(" --- ".$l, 5).' --- </th></tr><tr>';
			}
			if($row['likeit'] != $l) {
				$l = $row['likeit'];
				echo '</tr><tr style="border-top: 1px solid black;">';
				if($l > 0) {
					echo '<th colspan="3" style="background-color: #BBB;">' . str_repeat(" --- ".$l, 5).' --- </th></tr><tr>';
				} else {
					echo '<th colspan="3" style="background-color: #B55; color: #F00;">' . str_repeat(" --- ".$l, 5).' --- </th></tr><tr>';
				}
				$i = 0;
			}
			if($i > 0 & $i++ % 3 == 0) echo "</tr><tr>";
			echo '<td style=""><div style="position: relative;"><img src="'.$row['imagename'].'" /><div style="position: absolute; bottom: 0px; left: 0px; width: 100%; color:white; text-align: center; white-space: nowrap; overflow: hidden; background-color: #4449;">'.$row['viewed'].' / Views: '.$row['views'].' / Likes: '.$row['likeit'].'<br/>'.basename($row['imagename']).'</div><div style="position: absolute; bottom: 0px; right: 5px; white-space: nowrap; overflow: hidden;"><a style="text-decoration: none;" target="_blank" href="' . $GLOBALS['CONFIG']['INKY_URL'] . '/show/' . $row['imagename'] . '">Show</a><br>&nbsp;</div></div></td>';
		}
		echo "</tr></table>";
		echo '</body></html>';
	}
}

?>