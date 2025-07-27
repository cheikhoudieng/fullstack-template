// frontend/config-overrides.js
const BundleTracker = require('webpack-bundle-tracker');
// const path = require('path');
// console.log('*** Le fichier config-overrides.js est en cours de lecture ! ***');

module.exports = function override(config, env) {
  config.resolve.alias = config.resolve.alias || {};

  config.plugins.push(
    new BundleTracker({
      path: __dirname, // Chemin où le fichier sera généré (ici, la racine de 'frontend/')
      filename: 'webpack-stats.json', // Nom du fichier
    })
  );

  // Optionnel: Pour le développement, s'assurer que publicPath est correct si assets sont sur localhost:3000
  if (env === 'development' && config.output) {
    config.output.publicPath = `http://192.168.1.27:${
      process.env.PORT || 3000
    }/`; // URL du serveur de dev CRA
  }

  // // Ajouter les alias pour forcer la résolution de react et react-dom
  // // vers la version installée dans le node_modules de l'application principale.
  // // C'est la clé pour résoudre les conflits avec `npm link`.
  // Object.assign(config.resolve.alias, {
  //   react: path.resolve('./node_modules/react'),
  //   'react-dom': path.resolve('./node_modules/react-dom'),
  // });

  return config;
};
