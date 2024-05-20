<?php
// Initiate Configuration Array
$GLOBALS['CONFIG'] = Array();

// Database Connection
$GLOBALS['CONFIG']['DB_DSN'] = 'sqlite:inky.sqlite';

// Timezone / Language
date_default_timezone_set('Europe/Berlin');
setlocale(LC_TIME, 'de_DE@euro', 'de_DE', 'de', 'de');

// Connect
try {
	$GLOBALS['DB'] = new PDO($GLOBALS['CONFIG']['DB_DSN']);
} catch(PDOException $e) {
	die('Connection failed: ' . $e->getMessage());
}

// Create DB
try {
    $stmt = $GLOBALS['DB']->query("SELECT * FROM settings");
} catch(PDOException $e) {
	$GLOBALS['DB']->exec("CREATE TABLE settings (s_key TEXT, s_value TEXT)");
	$GLOBALS['DB']->exec("CREATE TABLE images  (imagename TEXT, views NUMBER, likeit NUMBER, lastupdate NUMBER)");
	$GLOBALS['DB']->exec("CREATE TABLE history (imagename TEXT, viewed TEXT)");
}

// Process Call
if(isset($_REQUEST['inky'])) { // Called by inky.py
	if(isset($_REQUEST['likeit'])) { // Like it +/- button pressed
		$likeit = 1; if(intval($_REQUEST['likeit']) < 0) $likeit = -1;
		// Get Last Image
		$stmt = $GLOBALS['DB']->query("SELECT imagename FROM history ORDER BY viewed DESC LIMIT 1");
		$row = $stmt->fetch(PDO::FETCH_ASSOC);
		$imagename = $row["imagename"];
		// Update favorit counter
		$stmt = $GLOBALS['DB']->prepare("UPDATE images SET likeit = likeit + :likeit WHERE imagename = :imagename");
		$stmt->bindValue(':likeit'   , $likeit  , PDO::PARAM_INT);
		$stmt->bindValue(':imagename',$imagename, PDO::PARAM_STR);
		$stmt->execute();
		echo $imagename;
	} else { // Any other button pressed
		// Get pressed Button
		$button = 0; if(isset($_REQUEST['button'])) $button = intval($_REQUEST['button']);
		if($button == 6) { // Get random image from favorit list
			$stmt = $GLOBALS['DB']->query("SELECT imagename FROM images WHERE lastupdate > 0 AND likeit > 0 ORDER BY RANDOM() LIMIT 1");
		} else { // Get any random image
			$stmt = $GLOBALS['DB']->query("SELECT imagename FROM images WHERE lastupdate > 0 ORDER BY views, RANDOM() LIMIT 1");
		}
		$row = $stmt->fetch(PDO::FETCH_ASSOC);
		$imagename = $row["imagename"];

		if($button == 5) { // Update view counter
			$stmt = $GLOBALS['DB']->prepare("UPDATE images SET views = views + 1 WHERE imagename = :imagename");
			$stmt->bindValue(':imagename', $imagename, PDO::PARAM_STR);
			$stmt->execute();
		}

		// Write History
		$stmt = $GLOBALS['DB']->prepare("INSERT INTO history (viewed, imagename) VALUES (datetime('now'), :imagename)");
		$stmt->bindValue(':imagename', $imagename, PDO::PARAM_STR);
		$stmt->execute();

		// Output Image
		$im = imagecreatefrompng($imagename);
		if($e = error_get_last()) {
			print_r($e);		
		} else {
			header('Content-type: image/png');
			ImagePNG($im);
			ImageDestroy($im);
		}
	}
} else {
	// Called by Browser
	if(isset($_REQUEST['update'])) { // Scan FS for new images
		echo '<a href="?"><button>Back</button></a>';
		// Get lowest View Count
		$stmt = $GLOBALS['DB']->query("SELECT min(views) -1 as min_views FROM images WHERE views > 0");
		$row = $stmt->fetch(PDO::FETCH_ASSOC);
		$min_views = $row['min_views'];
		if(!$min_views) $min_views = 0;
		// Mark all images as deleted
		$GLOBALS['DB']->exec("UPDATE images SET lastupdate = 0");
		// Read Directory
		echo "<table>";
		$files = glob("./images/*.png");
		for($i = 0;$i < count($files);$i++) {
			$stmt = $GLOBALS['DB']->prepare("UPDATE images SET lastupdate = 1 WHERE imagename = :imagename");
			$stmt->bindValue(':imagename', $files[$i], PDO::PARAM_STR);
			$stmt->execute();
			if($stmt->rowCount() == 0) {
				$stmt = $GLOBALS['DB']->prepare("INSERT INTO images (imagename, views, lastupdate, likeit) VALUES (:imagename, :views, 1, 0)");
				$stmt->bindValue(':imagename', $files[$i], PDO::PARAM_STR);
				$stmt->bindValue(':views'    , $min_views, PDO::PARAM_INT);
				$stmt->execute();
				echo "<tr style='background-color:yellow;'><td>" . $files[$i] . "</td><td>NEW</td>";
			} else {
				$stmt = $GLOBALS['DB']->prepare("SELECT views FROM images WHERE imagename = :imagename");
				$stmt->bindValue(':imagename', $files[$i], PDO::PARAM_STR);
				$stmt->execute();
				$row = $stmt->fetch(PDO::FETCH_ASSOC);
				echo "<tr><td>" . $files[$i] . "</td><td>".$row['views']."</td>";
			}
			echo "</tr>";
		}
		echo "</table>";
	} else if(isset($_REQUEST['single'])) { // Show random image
		echo '<a href="?"><button>Back</button></a>';
		echo '<br/><br/>';

		// Get random inage
		$stmt = $GLOBALS['DB']->query("SELECT imagename FROM images WHERE lastupdate > 0 ORDER BY views, RANDOM() LIMIT 1");
		$row = $stmt->fetch(PDO::FETCH_ASSOC);
		$imagename = $row["imagename"];

		// Output
		echo '<img src="'.$imagename.'" />';
	} else {
		// Show list of images
		echo '<a href="?update=1"><button>Update Database</button></a>&nbsp;';
		echo '<a href="?single=1"><button>Get single image</button></a>';
		echo '<br/><br/>';

		$i = 0;
		echo '<table style="border: 1px solid black; border-collapse: collapse;">';
		echo '<tr><th colspan="3" style="font-size: 2em; border-bottom: 1px solid black;">Last Viewed</th></tr>';
		echo '<tr>';
		$stmt = $GLOBALS['DB']->query("SELECT ih.imagename, ih.viewed, ii.views, ii.likeit FROM history ih JOIN images ii ON ii.imagename = ih.imagename ORDER BY ih.viewed DESC LIMIT 6");
		while($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
			if($i > 0 & $i++ % 3 == 0) echo "</tr><tr>";
			echo '<td style=""><div style="position: relative;"><img src="'.$row['imagename'].'" /><div style="position: absolute; bottom: 0px; left: 0px; width: 100%; color:white; text-align: center; white-space: nowrap; overflow: hidden; background-color: #4449;">'.$row['viewed'].' / Views: '.$row['views'].' / Likes: '.$row['likeit'].'<br/>'.basename($row['imagename']).'</div></div></td>';
		}
		echo '</tr></table>';

		echo '<br/><br/>';

		$i = 0;
		echo '<table style="border: 1px solid black; border-collapse: collapse;">';
		echo '<tr><th colspan="3" style="font-size: 2em; border-bottom: 1px solid black;">Favorits</th></tr>';
		echo '<tr>';
		$stmt = $GLOBALS['DB']->query("SELECT imagename, views, likeit FROM images WHERE likeit > 0 ORDER BY likeit, imagename");
		while($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
			if($i > 0 & $i++ % 3 == 0) echo "</tr><tr>";
			echo '<td style=""><div style="position: relative;"><img src="'.$row['imagename'].'" /><div style="position: absolute; bottom: 0px; left: 0px; width: 100%; color:white; text-align: center; white-space: nowrap; overflow: hidden; background-color: #4449;">Views: '.$row['views'].' / Likes: '.$row['likeit'].'<br/>'.basename($row['imagename']).'</div></div></td>';
		}
		echo "</tr></table>";

	}
}

?>