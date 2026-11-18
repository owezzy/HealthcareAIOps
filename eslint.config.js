import eslint from '@eslint/js';
import angular from 'angular-eslint';
import tseslint from 'typescript-eslint';

export default tseslint.config(
  {
    files: [
      'apps/web/**/*.{js,cjs,mjs}',
      'services/copilot-runtime/**/*.{js,cjs,mjs}',
    ],
    extends: [eslint.configs.recommended],
    rules: {
      '@typescript-eslint/no-require-imports': 'off',
    },
  },
  {
    files: ['apps/web/tailwind.config.js'],
    languageOptions: {
      globals: {
        __dirname: 'readonly',
        module: 'readonly',
        require: 'readonly',
      },
    },
  },
  {
    files: ['apps/web/**/*.{ts,mts}', 'services/copilot-runtime/**/*.{ts,mts}'],
    extends: [eslint.configs.recommended, ...tseslint.configs.recommended],
  },
  {
    files: ['apps/web/**/*.{ts,mts}'],
    extends: [...angular.configs.tsRecommended],
  },
  {
    files: ['apps/web/**/*.html'],
    extends: [...angular.configs.templateRecommended],
  },
  {
    ignores: [
      '**/dist/**',
      '**/build/**',
      '**/coverage/**',
      '**/node_modules/**',
      'apps/web/src/@fuse/**',
    ],
  }
);
