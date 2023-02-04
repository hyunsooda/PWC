{-# LANGUAGE OverloadedStrings #-}

module Main where

import Prelude hiding (cycle)
import Control.Lens
import Control.Monad
import Control.Monad.Writer
import Control.Monad.Catch
import qualified Data.ByteString.Lazy.Char8 as C
import Data.Foldable
import Data.List hiding (cycle)
import System.FilePath.Posix
import System.Console.ANSI
import System.Directory
import System.IO
import System.Process
import Network.Wreq
import Options.Applicative as Opt
import Text.Printf

data Err =
  UnsupportedGitLabSVN
    | RepoNotFound String
    | HttpGetError String String


data Params = Params {
                     conference :: String
                     , year :: String
                     , cycle :: String
                     , output :: String
                     , maxSize :: Maybe String
                     } deriving Show

instance Show Err where
  show UnsupportedGitLabSVN = "gitlab is not currently supported"
  show (RepoNotFound title) = "Failed to find repository: " ++ title
  show (HttpGetError title repoLink) =
    "Http(s) request error: " ++ "(title: " ++ title ++ ") (link: " ++ repoLink ++ ")"

parseHyperlink :: String -> WriterT [String] IO ()
parseHyperlink filePath = do
  txt <- liftIO $ readFile filePath
  let links = lines txt
      githubLinks = filterLink "https://github.com" links
      gitlabLinks = filterLink "https://gitlab.com" links
      title =
        map (\c -> if c == '_' then '/' else c) (takeBaseName filePath)
   in if null gitlabLinks
        then do
          log <- liftIO $ printQueryResult title githubLinks
          tell [log]
        else do
          err <- liftIO $ gitLabUnsupported
          tell [err]
  where
    filterLink prefix t = mkUniq $ filter (isPrefixOf prefix) t

    findRepo title repoLinks = do
      links <- filterM (isTargetRepo title) repoLinks
      if length links == 1
        then pure $ Just $ head links
        else pure $ Nothing

    printQueryResult title githubLinks = do
      link <- findRepo title githubLinks
      case link of
        Just link' -> do
          let titleWithLink = title ++ " --> " ++ link'
          setSGR [SetColor Foreground Vivid Green]
          print $ titleWithLink
          setSGR [Reset]
          pure titleWithLink
        Nothing -> do
          let repoNotFound = RepoNotFound title
          printErr repoNotFound
          pure $ show repoNotFound

    gitLabUnsupported = do
      printErr UnsupportedGitLabSVN
      pure $ show UnsupportedGitLabSVN


mkUniq :: (Ord a) => [a] -> [a]
mkUniq = map head . group . sort

isTargetRepo :: String -> String -> IO Bool
isTargetRepo title repoLink = do
  resp <- try (get repoLink) :: IO (Either SomeException (Response C.ByteString))
  case resp of
    Left err -> (printErr $ HttpGetError title repoLink) >> pure False
    Right r' ->
      let content = C.unpack (r' ^. responseBody)
       in pure $ isInfixOf title content

printErr :: Err -> IO ()
printErr errTyp =
  setSGR [SetColor Foreground Vivid Red] >> print errTyp >> setSGR [Reset]

runExtractor :: String -> WriterT [String] IO ()
runExtractor dir = do
  files <- liftIO $ getDirectoryContents dir
  traverse_ extractRepo files
    where
      extractRepo file =
        when (file /= "." && file /= "..") $ parseHyperlink (joinPath [dir, file])


main :: IO ()
main = do
  execParser opts >>= run
    where
      run params = do
        putStrLn "iterate pdf extraction..."
        let outputDir = output params
            outputFile = joinPath [outputDir, "result.txt"]
            cmdTemplate =
              printf "python3 extract.py -c %s -y %s -l %s -o %s"
              (conference params) (year params) (cycle params) outputDir
            cmdStr = case maxSize params of
                       Just maxSize' -> printf "%s -m %s" cmdTemplate maxSize'
                       Nothing -> cmdTemplate
        callCommand cmdStr

        (_, logs) <- runWriterT (runExtractor outputDir)
        out <- openFile outputFile WriteMode
        hPutStr out $ unlines logs
        hClose out

      opts = info (mkParams <**> helper)
                  (fullDesc <> progDesc "PWC (Paper With Code)")

mkParams :: Opt.Parser Params
mkParams =
  Params
  <$> strOption (long "conference" <> short 'c' <> help "target conference name (usenix | ccs | ndss | s&p)")
  <*> strOption (long "year" <> short 'y' <> help "publication year")
  <*> strOption (long "cycle" <> short 'l' <> help "cycle (spring | summer | fall | winter)")
  <*> strOption (long "output" <> short 'o' <> help "output path")
  <*> optional (strOption (long "maxsize" <> short 'm' <> help "allowed pdf max size to be extracted"))
